package main

import (
	"log"
	"os"

	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

var DB *gorm.DB

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
