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
	"context"
	"fmt"
	"internal/database"
	"internal/handlers"
	"internal/telemetry"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"go.opentelemetry.io/contrib/instrumentation/github.com/gin-gonic/gin/otelgin"
	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
)

// --- Main API Entrypoint ---

func main() {
	// Initialize Telemetry
	projectID := os.Getenv("GOOGLE_CLOUD_PROJECT")
	if projectID == "" {
		fmt.Println("Warning: GOOGLE_CLOUD_PROJECT not set. Telemetry might fail or use default.")
	}

	shutdown, err := telemetry.InitTelemetry(context.Background(), projectID, "building-permit-api")
	if err != nil {
		log.Printf("Failed to initialize telemetry: %v", err)
	} else {
		defer func() {
			if err := shutdown(context.Background()); err != nil {
				log.Printf("Telemetry shutdown failed: %v", err)
			}
		}()
	}

	// Initialize SQLite Database
	database.InitDB()

	r := gin.Default()

	// Add OpenTelemetry middleware
	r.Use(otelgin.Middleware("building-plan-api"))

	// Setup CORS to allow our frontend to make requests
	r.Use(cors.New(cors.Config{
		AllowOrigins:     []string{"*"}, // in production restrict this to frontend URL
		AllowMethods:     []string{"POST", "GET", "OPTIONS", "DELETE"},
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

	// Add the new API routes
	api := r.Group("/api")
	{
		api.POST("/login", handlers.LoginHandler)
		api.POST("/analyze-plan", handlers.AnalyzePlanHandler)
		api.GET("/users/:id/properties", handlers.GetUserPropertiesHandler)
		api.POST("/users/:id/properties", handlers.CreateUserPropertyHandler)
		api.GET("/properties/:id/permits", handlers.GetPropertyPermitsHandler)
		api.POST("/properties/:id/permits", handlers.CreatePropertyPermitHandler)
		api.GET("/permits/:id", handlers.GetPermitHandler)
		api.DELETE("/permits/:id", handlers.DeletePermitHandler)
		api.POST("/chat", handlers.ChatHandler)
		api.POST("/contractor-chat", handlers.ContractorChatHandler)
	}

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	wrappedHandler := otelhttp.NewHandler(r, "building-plan-api")

	fmt.Printf("Starting API Gateway with OTel HTTP Server instrumentation on :%s\n", port)
	if err := http.ListenAndServe(":"+port, wrappedHandler); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}
