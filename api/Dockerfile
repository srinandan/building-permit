# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Build stage
FROM golang:1.24-alpine AS build
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
# CGO_ENABLED=1 is required for go-sqlite3
RUN apk add --no-cache gcc musl-dev
RUN CGO_ENABLED=1 GOOS=linux go build -o api-server .

# Run stage
FROM alpine:latest
WORKDIR /app
RUN apk add --no-cache ca-certificates tzdata sqlite
COPY --from=build /app/api-server .
EXPOSE 8080
ENV PORT=8080
ENV DB_NAME=/app/data/building_plans.db
# Create a volume for the sqlite database to persist
VOLUME ["/app/data"]
CMD ["./api-server"]
