// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package handlers

import (
	"bytes"
	"encoding/json"
	"internal/database"
	"internal/models"
	"io"
	"log"
	"mime/multipart"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/modelcontextprotocol/go-sdk/mcp"
	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
)

var agentHTTPClient = &http.Client{
	Transport: otelhttp.NewTransport(http.DefaultTransport),
	Timeout:   180 * time.Second,
}

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

	var user models.User
	// Find or Create user based on email
	result := database.DB.Where("email = ?", req.Email).First(&user)
	if result.Error != nil {
		// Create new user
		user = models.User{
			Email: req.Email,
			Name:  req.Email, // default to email for name
		}
		database.DB.Create(&user)
	}

	c.JSON(http.StatusOK, user)
}

func GetUserPropertiesHandler(c *gin.Context) {
	userId := c.Param("id")
	properties := []models.Property{}
	database.DB.Where("user_id = ?", userId).Find(&properties)
	c.JSON(http.StatusOK, properties)
}

func CreateUserPropertyHandler(c *gin.Context) {
	userId := c.Param("id")
	var property models.Property
	if err := c.ShouldBindJSON(&property); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request"})
		return
	}

	var user models.User
	if err := database.DB.First(&user, userId).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "User not found"})
		return
	}

	// Check if a property with this address already exists for this user (prevent duplicate creation from strict mode)
	var existingProperty models.Property
	if err := database.DB.Where("user_id = ? AND address = ?", user.ID, property.Address).First(&existingProperty).Error; err == nil {
		c.JSON(http.StatusOK, existingProperty)
		return
	}

	property.UserID = user.ID
	database.DB.Create(&property)
	c.JSON(http.StatusCreated, property)
}

func GetPropertyPermitsHandler(c *gin.Context) {
	propertyId := c.Param("id")
	permits := []models.Permit{}
	// Preload the latest submission for each permit
	database.DB.Preload("Submissions").Where("property_id = ?", propertyId).Find(&permits)
	c.JSON(http.StatusOK, permits)
}

func CreatePropertyPermitHandler(c *gin.Context) {
	propertyId := c.Param("id")
	var permit models.Permit
	if err := c.ShouldBindJSON(&permit); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request"})
		return
	}

	var property models.Property
	if err := database.DB.First(&property, propertyId).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Property not found"})
		return
	}

	permit.PropertyID = property.ID
	permit.Status = "Draft" // Initial status
	database.DB.Create(&permit)
	c.JSON(http.StatusCreated, permit)
}

func GetPermitHandler(c *gin.Context) {
	permitId := c.Param("id")
	var permit models.Permit
	if err := database.DB.Preload("Submissions").First(&permit, permitId).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Permit not found"})
		return
	}
	c.JSON(http.StatusOK, permit)
}

func DeletePermitHandler(c *gin.Context) {
	permitId := c.Param("id")

	// First, delete associated submissions to maintain referential integrity
	database.DB.Where("permit_id = ?", permitId).Delete(&models.PermitSubmission{})

	// Delete the permit
	result := database.DB.Delete(&models.Permit{}, permitId)
	if result.Error != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to delete permit"})
		return
	}

	// Adding CORS headers explicitly on DELETE can sometimes help if preflight is flaky,
	// though Gin handles it. Let's ensure standard JSON response.
	c.JSON(http.StatusOK, gin.H{"message": "Permit deleted successfully"})
}

func UpdatePermitStatusHandler(c *gin.Context) {
	permitId := c.Param("id")

	var req struct {
		Status string `json:"status" binding:"required"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request"})
		return
	}

	var permit models.Permit
	if err := database.DB.First(&permit, permitId).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Permit not found"})
		return
	}

	permit.Status = req.Status
	database.DB.Save(&permit)

	c.JSON(http.StatusOK, permit)
}

// Struct to extract status from Agent JSON response
type AgentResponse struct {
	Status           string        `json:"status"`
	Violations       []interface{} `json:"violations"`
	ApprovedElements []string      `json:"approved_elements"`
}

func ChatHandler(c *gin.Context) {
	agentURL := os.Getenv("AGENT_URL")
	if agentURL == "" {
		agentURL = "http://127.0.0.1:8000/analyze" // default local Python agent URL
	}

	// Convert /analyze to /chat
	if strings.HasSuffix(agentURL, "/analyze") {
		agentURL = strings.TrimSuffix(agentURL, "/analyze") + "/chat"
	} else if !strings.HasSuffix(agentURL, "/chat") {
		agentURL = agentURL + "/chat"
	}

	// Read the raw JSON payload from the request
	body, err := io.ReadAll(c.Request.Body)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Failed to read request body"})
		return
	}
	defer c.Request.Body.Close()

	// Forward the JSON payload to the Python agent
	req, err := http.NewRequestWithContext(c.Request.Context(), "POST", agentURL, bytes.NewBuffer(body))
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create request to agent"})
		return
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := agentHTTPClient.Do(req)
	if err != nil {
		log.Printf("Error calling agent chat endpoint: %v", err)
		c.JSON(http.StatusBadGateway, gin.H{"error": "Failed to communicate with AI agent"})
		return
	}
	defer resp.Body.Close()

	// Read the response from the agent
	agentResponse, err := io.ReadAll(resp.Body)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to read agent response"})
		return
	}

	// Return the response back to the client
	c.Data(resp.StatusCode, "application/json", agentResponse)
}

func ContractorChatHandler(c *gin.Context) {
	agentURL := os.Getenv("AGENT_URL")
	if agentURL == "" {
		agentURL = "http://127.0.0.1:8001/chat" // default local agent URL
	} else {
		if !strings.HasSuffix(agentURL, "/chat") {
			agentURL = strings.TrimSuffix(agentURL, "/") + "/chat"
		}
	}

	// Read the raw JSON payload from the request
	body, err := io.ReadAll(c.Request.Body)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Failed to read request body"})
		return
	}
	defer c.Request.Body.Close()

	// Forward the JSON payload to the Python agent
	req, err := http.NewRequestWithContext(c.Request.Context(), "POST", agentURL, bytes.NewBuffer(body))
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create request to agent"})
		return
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := agentHTTPClient.Do(req)
	if err != nil {
		log.Printf("Error calling agent contractor-chat endpoint: %v", err)
		c.JSON(http.StatusBadGateway, gin.H{"error": "Failed to communicate with AI agent"})
		return
	}
	defer resp.Body.Close()

	// Read the response from the agent
	agentResponse, err := io.ReadAll(resp.Body)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to read response from agent"})
		return
	}

	// Forward the agent's response back to the client
	c.Data(resp.StatusCode, "application/json", agentResponse)
}

func AnalyzePlanHandler(c *gin.Context) {
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
	} else {
		if !strings.HasSuffix(agentURL, "/analyze") {
			agentURL = strings.TrimSuffix(agentURL, "/") + "/analyze"
		}
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
	req, err := http.NewRequestWithContext(c.Request.Context(), "POST", agentURL, body)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create request to agent"})
		return
	}

	// Set the content type to the boundary of the multipart writer
	req.Header.Set("Content-Type", writer.FormDataContentType())

	// Execute the request
	resp, err := agentHTTPClient.Do(req)
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
		var permit models.Permit
		if err := database.DB.First(&permit, permitIDStr).Error; err == nil {
			// Create a new submission history record
			submission := models.PermitSubmission{
				PermitID:       permit.ID,
				FileName:       file.Filename,
				AnalysisStatus: analysisStatus,
				ReportJSON:     string(agentResponse),
			}
			database.DB.Create(&submission)

			// Update Permit status to reflect the latest analysis
			permit.Status = analysisStatus
			database.DB.Save(&permit)
		}
	}

	// Pass the agent's response back to the client directly
	c.Data(resp.StatusCode, "application/json", agentResponse)
}

// GetPropertiesByEmailHandler calls the local assessor MCP server to get properties by email using streamable http
func GetPropertiesByEmailHandler(c *gin.Context) {
	email := c.Param("email")

	assessorURL := os.Getenv("ASSESSOR_URL")
	if assessorURL == "" {
		assessorURL = "http://127.0.0.1:8002/mcp"
	}

	// Create a new client, with no features.
	client := mcp.NewClient(&mcp.Implementation{Name: "mcp-client", Version: "v1.0.0"}, nil)
	transport := &mcp.StreamableClientTransport{
		Endpoint: assessorURL,
		HTTPClient: agentHTTPClient,
		MaxRetries: 3,
	}

	cs, err := client.Connect(c.Request.Context(), transport, nil)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to connect to Assessor MCP"})
		return
	}
	defer cs.Close()

	result, err := cs.CallTool(c.Request.Context(), &mcp.CallToolParams{
		Name:      "get_user_properties",
		Arguments: map[string]any{"email": email},
	})
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to call MCP tool"})
		return
	}

	for _, content := range result.Content {
		if textContent, ok := content.(*mcp.TextContent); ok {
			var resp models.UserPropertiesResponse
			if err := json.Unmarshal([]byte(textContent.Text), &resp); err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to parse properties response"})
				return
			}
			c.JSON(http.StatusOK, resp)
			return
		}
	}

	// Fallback to returning raw result if parsing fails
	c.JSON(http.StatusOK, result)
}

type headerTransport struct {
	base   http.RoundTripper
	header http.Header
}

func (t *headerTransport) RoundTrip(req *http.Request) (*http.Response, error) {
	req = req.Clone(req.Context())
	for k, vv := range t.header {
		for _, v := range vv {
			req.Header.Add(k, v)
		}
	}
	if t.base == nil {
		return http.DefaultTransport.RoundTrip(req)
	}
	return t.base.RoundTrip(req)
}

// GetMapDataHandler calls the Google Maps MCP Server
func GetMapDataHandler(c *gin.Context) {
	var reqBody models.MapSearchRequest
	if err := c.ShouldBindJSON(&reqBody); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request"})
		return
	}

	apiKey := os.Getenv("GOOGLE_MAPS_API_KEY")
	if apiKey == "" {
		// Log error but we could try sending anyway if it works anonymously? Maps API usually requires key.
		log.Println("Warning: GOOGLE_MAPS_API_KEY environment variable is not set")
	}

	// Create a new client, with no features.
	client := mcp.NewClient(&mcp.Implementation{Name: "mcp-client", Version: "v1.0.0"}, nil)

	// Create a custom transport to inject the API key header
	var customClient *http.Client
	if apiKey != "" {
		customClient = &http.Client{
			Transport: &headerTransport{
				base:   agentHTTPClient.Transport,
				header: http.Header{"x-goog-api-key": []string{apiKey}},
			},
		}
	}

	transport := &mcp.StreamableClientTransport{
		Endpoint:   "https://mapstools.googleapis.com/mcp",
		HTTPClient: customClient,
	}

	cs, err := client.Connect(c.Request.Context(), transport, nil)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to connect to Maps MCP server"})
		return
	}
	defer cs.Close()

	result, err := cs.CallTool(c.Request.Context(), &mcp.CallToolParams{
		Name:      "search_places",
		Arguments: map[string]any{"text_query": reqBody.Address},
	})
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to call MCP tool"})
		return
	}

	for _, content := range result.Content {
		if textContent, ok := content.(*mcp.TextContent); ok {
			// The MCP response text is already JSON, send it directly
			c.Data(http.StatusOK, "application/json", []byte(textContent.Text))
			return
		}
	}

	// Fallback to returning raw result if no text content
	c.JSON(http.StatusOK, result)
}

