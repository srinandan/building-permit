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
	"context"
	"log"

	"google.golang.org/api/agentregistry/v1alpha"
	"google.golang.org/api/cloudresourcemanager/v1"
)

func Init() (*agentregistry.APIService, error) {
	log.Println("Initialize client")
	ctx := context.Background()
	svc, err := agentregistry.NewService(ctx)
	return svc, err
}

func FindMapsMCP(svc *agentregistry.APIService, projectID string) (string, error) {
	const location = "global"
	projectNumber, err := getProjectNumber(projectID)
	if err != nil {
		return "", fmt.Errorf("error getting project number: %v", err)
	}
	parent := fmt.Sprintf("projects/%s/locations/%s", projectNumber, location)
	targetID := fmt.Sprintf("urn:mcp:googleapis.com:projects:%s:locations:%s:mapstools", projectNumber, location)
	filter := fmt.Sprintf("mcpServerId = %q", targetID)

	resp, err := svc.Projects.Locations.McpServers.List(parent).
		Filter(filter).
		PageSize(1).
		Do()
	if err != nil {
		return "", fmt.Errorf("error searching for MCP server: %v", err)
	}

	// 1. Check if the server exists
	if len(resp.McpServers) == 0 {
		return "", fmt.Errorf("no MCP server found with ID: %s", targetID)
	}

	server := resp.McpServers[0]

	// 2. Check if the server has any interfaces defined
	if len(server.Interfaces) == 0 {
		return "", fmt.Errorf("MCP server found, but it has no interfaces defined")
	}

	return server.Interfaces[0].Url, nil
}

func getProjectNumber(projectID string) (string, error) {
	log.Println("Fetch project number")
	ctx := context.Background()
	service, err := cloudresourcemanager.NewService(ctx)
	if err != nil {
		return "", fmt.Errorf("error creating Resource Manager service: %v", err)
	}

	project, err := service.Projects.Get(projectID).Do()
	if err != nil {
		return "", fmt.Errorf("error getting project: %v", err)
	}

	return fmt.Sprintf("%d", project.ProjectNumber), nil
}
