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

package models

import (
	"time"

	"gorm.io/gorm"
)

type User struct {
	gorm.Model
	ID         uint       `gorm:"primaryKey" json:"id"`
	Email      string     `gorm:"uniqueIndex" json:"email"`
	Name       string     `json:"name"`
	CreatedAt  time.Time  `json:"created_at"`
	UpdatedAt  time.Time  `json:"updated_at"`
	Properties []Property `gorm:"foreignKey:UserID" json:"properties"`
}

type Property struct {
	gorm.Model
	ID        uint      `gorm:"primaryKey" json:"id"`
	UserID    uint      `json:"user_id"`
	Address   string    `json:"address"`
	City      string    `json:"city"`
	ZipCode   string    `json:"zip_code"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
	Permits   []Permit  `gorm:"foreignKey:PropertyID" json:"permits"`
}

type Permit struct {
	gorm.Model
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
	gorm.Model
	ID             uint      `gorm:"primaryKey" json:"id"`
	PermitID       uint      `json:"permit_id"`
	FileName       string    `json:"file_name"`
	AnalysisStatus string    `json:"analysis_status"`
	ReportJSON     string    `json:"report_json"` // Store the JSON report string
	CreatedAt      time.Time `json:"created_at"`
}

// UserPropertiesResponse captures the response from the get_user_properties MCP tool
type UserPropertiesResponse struct {
	gorm.Model
	Properties []string `json:"properties"`
	Error      string   `json:"error,omitempty"`
}

type MapSearchRequest struct {
	Address string `json:"address" binding:"required"`
}
