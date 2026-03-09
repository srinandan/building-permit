package main

import (
	"net/http"
	"github.com/gin-gonic/gin"
)

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
