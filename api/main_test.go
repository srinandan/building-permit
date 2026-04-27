package main

import (
	"bytes"
	"encoding/json"
	"internal/database"
	"internal/handlers"
	"internal/models"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"

	"github.com/gin-gonic/gin"
)

func setupRouter() *gin.Engine {
	// Use an in-memory SQLite database for testing
	os.Setenv("DB_NAME", ":memory:")
	database.InitDB()

	// Create some dummy data
	db := database.DB

	user := models.User{
		Email: "test@example.com",
		Name:  "Test User",
	}
	db.Create(&user)

	db.Create(&models.Property{
		UserID:  user.ID,
		Address: "123 Test St",
	})
	db.Create(&models.Property{
		UserID:  user.ID,
		Address: "456 Test Ave",
	})

	r := gin.Default()
	gin.SetMode(gin.TestMode)

	r.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status": "ok",
		})
	})

	api := r.Group("/api")
	api.POST("/login", handlers.LoginHandler)
	api.GET("/users/:id/properties", handlers.GetUserPropertiesHandler)
	api.POST("/users/:id/properties", handlers.CreateUserPropertyHandler)

	// Skip GetPropertiesByEmailHandler as it requires network to MCP server
	// api.GET("/users/email/:email/properties", handlers.GetPropertiesByEmailHandler)

	api.GET("/properties/:id/permits", handlers.GetPropertyPermitsHandler)
	api.POST("/properties/:id/permits", handlers.CreatePropertyPermitHandler)
	api.GET("/permits/:id", handlers.GetPermitHandler)
	api.DELETE("/permits/:id", handlers.DeletePermitHandler)
	api.PATCH("/permits/:id/status", handlers.UpdatePermitStatusHandler)

	return r
}

func TestHealthCheck(t *testing.T) {
	r := setupRouter()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/health", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status %d but got %d", http.StatusOK, w.Code)
	}

	expectedBody := `{"status":"ok"}`
	if w.Body.String() != expectedBody {
		t.Errorf("Expected body %s but got %s", expectedBody, w.Body.String())
	}
}

func TestLoginHandler(t *testing.T) {
	r := setupRouter()

	body := []byte(`{"email": "test@example.com", "password": "password"}`)
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/api/login", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")

	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status %d but got %d", http.StatusOK, w.Code)
	}

	var user models.User
	json.Unmarshal(w.Body.Bytes(), &user)

	if user.Email != "test@example.com" {
		t.Errorf("Expected email 'test@example.com' but got %s", user.Email)
	}
}

func TestGetUserPropertiesHandler(t *testing.T) {
	r := setupRouter()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/api/users/1/properties", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status %d but got %d", http.StatusOK, w.Code)
	}
}

func TestCreateUserPropertyHandler(t *testing.T) {
	r := setupRouter()

	body := []byte(`{"user_email": "test2@example.com", "address": "789 New St", "city": "San Jose", "zip_code": "95112"}`)
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/api/users/1/properties", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")

	r.ServeHTTP(w, req)

	if w.Code != http.StatusCreated {
		t.Errorf("Expected status %d but got %d", http.StatusCreated, w.Code)
	}
}

func TestGetPropertyPermitsHandler(t *testing.T) {
	r := setupRouter()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/api/properties/1/permits", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status %d but got %d", http.StatusOK, w.Code)
	}
}

func TestCreatePropertyPermitHandler(t *testing.T) {
	r := setupRouter()

	body := []byte(`{"property_id": 1, "title": "Electrical", "description": "Desc", "status": "Draft"}`)
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/api/properties/1/permits", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")

	r.ServeHTTP(w, req)

	if w.Code != http.StatusCreated {
		t.Errorf("Expected status %d but got %d", http.StatusCreated, w.Code)
	}
}

func TestGetPermitHandler(t *testing.T) {
	r := setupRouter()

	// First create a permit
	db := database.DB
	permit := models.Permit{PropertyID: 1, Title: "Plumbing", Status: "Pending"}
	db.Create(&permit)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/api/permits/1", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status %d but got %d", http.StatusOK, w.Code)
	}
}

func TestUpdatePermitStatusHandler(t *testing.T) {
	r := setupRouter()

	// First create a permit
	db := database.DB
	permit := models.Permit{PropertyID: 1, Title: "Plumbing", Status: "Pending"}
	db.Create(&permit)

	body := []byte(`{"status": "Approved"}`)
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("PATCH", "/api/permits/1/status", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")

	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status %d but got %d", http.StatusOK, w.Code)
	}
}

func TestDeletePermitHandler(t *testing.T) {
	r := setupRouter()

	// First create a permit
	db := database.DB
	permit := models.Permit{PropertyID: 1, Title: "Plumbing", Status: "Pending"}
	db.Create(&permit)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("DELETE", "/api/permits/1", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status %d but got %d", http.StatusOK, w.Code)
	}
}
