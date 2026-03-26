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

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"go.opentelemetry.io/contrib/instrumentation/github.com/gin-gonic/gin/otelgin"
)

const serviceName = "building-permit-api"

func main() {
	// Initialize Telemetry
	projectID := os.Getenv("GOOGLE_CLOUD_PROJECT")
	if projectID == "" {
		fmt.Println("Warning: GOOGLE_CLOUD_PROJECT not set. Telemetry might fail or use default.")
	}

	location := os.Getenv("GOOGLE_CLOUD_LOCATION")
	if location == "" {
		fmt.Println("Warning: GOOGLE_CLOUD_LOCATION not set. Telemetry might fail or use default.")
	}

	shutdown, err := telemetry.InitTelemetry(context.Background(), projectID, location, serviceName)
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
	r.Use(otelgin.Middleware(serviceName))

	// Setup CORS to allow our frontend to make requests
	config := cors.DefaultConfig()
	config.AllowAllOrigins = true
	config.AllowMethods = []string{"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
	config.AllowHeaders = []string{"Origin", "Content-Length", "Content-Type", "Authorization", "traceparent", "tracestate"}
	r.Use(cors.New(config))

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

	r.Run(fmt.Sprintf(":%s", port))
}
