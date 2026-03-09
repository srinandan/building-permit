package main

import (
	"time"
)

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
