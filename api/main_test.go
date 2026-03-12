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

package main

import (
	"bytes"
	"mime/multipart"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"
	"time"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
)

func TestHealthCheck(t *testing.T) {
	// Set Gin to test mode
	gin.SetMode(gin.TestMode)

	r := gin.Default()
	r.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status": "ok",
		})
	})

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

func TestAnalyzePlanNoFile(t *testing.T) {
	gin.SetMode(gin.TestMode)

	r := gin.Default()
	r.POST("/api/analyze-plan", func(c *gin.Context) {
		// Mock implementation just to test missing file logic
		_, err := c.FormFile("file")
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "No file uploaded"})
			return
		}
	})

	w := httptest.NewRecorder()

	// Create empty multipart body
	body := &bytes.Buffer{}
	writer := multipart.NewWriter(body)
	writer.Close()

	req, _ := http.NewRequest("POST", "/api/analyze-plan", body)
	req.Header.Set("Content-Type", writer.FormDataContentType())

	r.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status %d but got %d", http.StatusBadRequest, w.Code)
	}

	expectedError := `{"error":"No file uploaded"}`
	if w.Body.String() != expectedError {
		t.Errorf("Expected error %s but got %s", expectedError, w.Body.String())
	}
}

func TestCORSFix(t *testing.T) {
	gin.SetMode(gin.TestMode)

	// Set ALLOWED_ORIGINS to control the test environment
	os.Setenv("ALLOWED_ORIGINS", "http://trusted.com,http://another-trusted.com")
	defer os.Unsetenv("ALLOWED_ORIGINS")

	// We need to trigger the logic in main() but without starting the server.
	// Since main() is a bit coupled, let's replicate the logic for testing.

	allowedOrigins := []string{
		"http://localhost:3000",
		"http://localhost:5173",
		"http://127.0.0.1:3000",
		"http://127.0.0.1:5173",
	}

	if envOrigins := os.Getenv("ALLOWED_ORIGINS"); envOrigins != "" {
		allowedOrigins = strings.Split(envOrigins, ",")
	}

	r := gin.New()
	r.Use(cors.New(cors.Config{
		AllowOrigins:     allowedOrigins,
		AllowMethods:     []string{"POST", "GET", "OPTIONS", "DELETE"},
		AllowHeaders:     []string{"Origin", "Content-Type"},
		ExposeHeaders:    []string{"Content-Length"},
		AllowCredentials: true,
		MaxAge:           12 * time.Hour,
	}))

	r.GET("/test", func(c *gin.Context) {
		c.Status(http.StatusOK)
	})

	tests := []struct {
		origin  string
		allowed bool
	}{
		{"http://trusted.com", true},
		{"http://another-trusted.com", true},
		{"http://malicious.com", false},
		{"http://localhost:3000", false}, // Overridden by env var in this test
	}

	for _, tt := range tests {
		w := httptest.NewRecorder()
		req, _ := http.NewRequest("GET", "/test", nil)
		req.Header.Set("Origin", tt.origin)
		r.ServeHTTP(w, req)

		got := w.Header().Get("Access-Control-Allow-Origin")
		if tt.allowed {
			if got != tt.origin {
				t.Errorf("Origin %s should be allowed, but got Access-Control-Allow-Origin: %s", tt.origin, got)
			}
		} else {
			if got == tt.origin || got == "*" {
				t.Errorf("Origin %s should NOT be allowed, but got Access-Control-Allow-Origin: %s", tt.origin, got)
			}
		}
	}
}
