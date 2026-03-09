package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"mime/multipart"
	"net/http"
	"os"
	"time"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

// --- Database & Models ---

var DB *gorm.DB

type User struct {
	ID        uint       `gorm:"primaryKey" json:"id"`
	Email     string     `gorm:"uniqueIndex" json:"email"`
	Name      string     `json:"name"`
	CreatedAt time.Time  `json:"created_at"`
	UpdatedAt time.Time  `json:"updated_at"`
	Properties []Property `gorm:"foreignKey:UserID" json:"properties"`
}

type Property struct {
	ID        uint       `gorm:"primaryKey" json:"id"`
	UserID    uint       `json:"user_id"`
	Address   string     `json:"address"`
	City      string     `json:"city"`
	ZipCode   string     `json:"zip_code"`
	CreatedAt time.Time  `json:"created_at"`
	UpdatedAt time.Time  `json:"updated_at"`
	Permits   []Permit   `gorm:"foreignKey:PropertyID" json:"permits"`
}

type Permit struct {
	ID          uint               `gorm:"primaryKey" json:"id"`
	PropertyID  uint               `json:"property_id"`
	Title       string             `json:"title"`
	Description string             `json:"description"`
	Status      string             `json:"status"` // e.g. "Draft", "Submitted", "Changes Suggested", "Approved"
	CreatedAt   time.Time          `json:"created_at"`
	UpdatedAt   time.Time          `json:"updated_at"`
	Submissions []PermitSubmission `gorm:"foreignKey:PermitID" json:"submissions"`
}

type PermitSubmission struct {
	ID              uint           `gorm:"primaryKey" json:"id"`
	PermitID        uint           `json:"permit_id"`
	FileName        string         `json:"file_name"`
	AnalysisStatus  string         `json:"analysis_status"`
	ReportJSON      string         `json:"report_json"` // Store the JSON report string
	CreatedAt       time.Time      `json:"created_at"`
}

func InitDB() {
	dbName := os.Getenv("DB_NAME")
	if dbName == "" {
		dbName = "building_plans.db"
	}

	db, err := gorm.Open(sqlite.Open(dbName), &gorm.Config{
		Logger: logger.Default.LogMode(logger.Info),
	})
	if err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}

	// Auto-migrate our models
	log.Println("Migrating database models...")
	err = db.AutoMigrate(&User{}, &Property{}, &Permit{}, &PermitSubmission{})
	if err != nil {
		log.Fatalf("Failed to migrate database: %v", err)
	}

	DB = db
	log.Println("Database connection established")
}

// --- Handlers ---

type LoginRequest struct {
	Email string `json:"email" binding:"required"`
	// Password ignored for simple login
}

func LoginHandler(c *gin.Context) {
	var req LoginRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request"})
		return
	}

	var user User
	// Find or Create user based on email
	result := DB.Where("email = ?", req.Email).First(&user)
	if result.Error != nil {
		// Create new user
		user = User{
			Email: req.Email,
			Name:  req.Email, // default to email for name
		}
		DB.Create(&user)
	}

	c.JSON(http.StatusOK, user)
}

func GetUserPropertiesHandler(c *gin.Context) {
	userId := c.Param("id")
	properties := []Property{}
	DB.Where("user_id = ?", userId).Find(&properties)
	c.JSON(http.StatusOK, properties)
}

func CreateUserPropertyHandler(c *gin.Context) {
	userId := c.Param("id")
	var property Property
	if err := c.ShouldBindJSON(&property); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request"})
		return
	}

	var user User
	if err := DB.First(&user, userId).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "User not found"})
		return
	}

	property.UserID = user.ID
	DB.Create(&property)
	c.JSON(http.StatusCreated, property)
}

func GetPropertyPermitsHandler(c *gin.Context) {
	propertyId := c.Param("id")
	permits := []Permit{}
	// Preload the latest submission for each permit
	DB.Preload("Submissions").Where("property_id = ?", propertyId).Find(&permits)
	c.JSON(http.StatusOK, permits)
}

func CreatePropertyPermitHandler(c *gin.Context) {
	propertyId := c.Param("id")
	var permit Permit
	if err := c.ShouldBindJSON(&permit); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request"})
		return
	}

	var property Property
	if err := DB.First(&property, propertyId).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Property not found"})
		return
	}

	permit.PropertyID = property.ID
	permit.Status = "Draft" // Initial status
	DB.Create(&permit)
	c.JSON(http.StatusCreated, permit)
}

func GetPermitHandler(c *gin.Context) {
	permitId := c.Param("id")
	var permit Permit
	if err := DB.Preload("Submissions").First(&permit, permitId).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Permit not found"})
		return
	}
	c.JSON(http.StatusOK, permit)
}

// Struct to extract status from Agent JSON response
type AgentResponse struct {
	Status           string        `json:"status"`
	Violations       []interface{} `json:"violations"`
	ApprovedElements []string      `json:"approved_elements"`
}

// --- Main API Entrypoint ---

func main() {
	// Initialize SQLite Database
	InitDB()

	r := gin.Default()

	// Setup CORS to allow our frontend to make requests
	r.Use(cors.New(cors.Config{
		AllowOrigins:     []string{"*"}, // in production restrict this to frontend URL
		AllowMethods:     []string{"POST", "GET", "OPTIONS"},
		AllowHeaders:     []string{"Origin", "Content-Type"},
		ExposeHeaders:    []string{"Content-Length"},
		AllowCredentials: true,
		MaxAge:           12 * time.Hour,
	}))

	r.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status": "ok",
		})
	})

	r.POST("/api/analyze-plan", func(c *gin.Context) {
		// Get the file from the form data
		file, err := c.FormFile("file")
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "No file uploaded"})
			return
		}

		// Open the file
		openedFile, err := file.Open()
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to open uploaded file"})
			return
		}
		defer openedFile.Close()

		// Prepare a multipart request to send to the Python agent
		agentURL := os.Getenv("AGENT_URL")
		if agentURL == "" {
			agentURL = "http://127.0.0.1:8000/analyze" // default local Python agent URL
		}

		// Create a buffer to hold the multipart body
		body := &bytes.Buffer{}
		writer := multipart.NewWriter(body)

		// Create a form file field named "file"
		part, err := writer.CreateFormFile("file", file.Filename)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create form file"})
			return
		}

		// Copy the uploaded file data to the form file field
		_, err = io.Copy(part, openedFile)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to copy file data"})
			return
		}

		// Close the multipart writer to finalize the payload
		err = writer.Close()
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to close multipart writer"})
			return
		}

		// Create a new HTTP POST request to the Python agent
		req, err := http.NewRequest("POST", agentURL, body)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create request to agent"})
			return
		}

		// Set the content type to the boundary of the multipart writer
		req.Header.Set("Content-Type", writer.FormDataContentType())

		// Execute the request
		client := &http.Client{Timeout: 60 * time.Second} // Agent analysis can take a while
		resp, err := client.Do(req)
		if err != nil {
			log.Printf("Error calling agent: %v", err)
			c.JSON(http.StatusBadGateway, gin.H{"error": "Failed to communicate with AI agent"})
			return
		}
		defer resp.Body.Close()

		// Read the agent's response
		agentResponse, err := io.ReadAll(resp.Body)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to read agent response"})
			return
		}

		// Pass the agent's response back to the client directly
		// Parse the agent response to get the status
		var agentResult struct {
			Status string `json:"status"`
		}

		err = json.Unmarshal(agentResponse, &agentResult)
		analysisStatus := "Analysis Complete" // Default
		if err == nil && agentResult.Status != "" {
			analysisStatus = agentResult.Status
		}

		// Note: At this point we don't have a Permit ID directly from the multipart form
		// Let's assume the client passes `permit_id` in the form
		permitIDStr := c.PostForm("permit_id")

		// If permit_id is provided, save it to the database
		if permitIDStr != "" {
			var permit Permit
			if err := DB.First(&permit, permitIDStr).Error; err == nil {
				// Create a new submission history record
				submission := PermitSubmission{
					PermitID:       permit.ID,
					FileName:       file.Filename,
					AnalysisStatus: analysisStatus,
					ReportJSON:     string(agentResponse),
				}
				DB.Create(&submission)

				// Update Permit status to reflect the latest analysis
				permit.Status = analysisStatus
				DB.Save(&permit)
			}
		}

		// Pass the agent's response back to the client directly
		c.Data(resp.StatusCode, "application/json", agentResponse)
	})

	// Add the new API routes
	api := r.Group("/api")
	{
		api.POST("/login", LoginHandler)
		api.GET("/users/:id/properties", GetUserPropertiesHandler)
		api.POST("/users/:id/properties", CreateUserPropertyHandler)
		api.GET("/properties/:id/permits", GetPropertyPermitsHandler)
		api.POST("/properties/:id/permits", CreatePropertyPermitHandler)
		api.GET("/permits/:id", GetPermitHandler)
	}

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	fmt.Printf("Starting API Gateway on :%s\n", port)
	r.Run(":" + port)
}
