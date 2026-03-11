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
	"testing"


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
