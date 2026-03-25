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
FROM golang:1.25-alpine AS build
WORKDIR /app
COPY go.mod go.sum ./
COPY internal/ ./internal/
RUN go mod download
COPY . .
# CGO_ENABLED=1 is required for go-sqlite3
RUN apk add --no-cache gcc musl-dev
RUN CGO_ENABLED=1 GOOS=linux GOARCH=amd64 go build -trimpath -buildvcs=true -a -gcflags='all="-l"' -ldflags='-s -w -extldflags "-static"' -o api-server .

# Run stage
FROM gcr.io/distroless/static-debian11:debug-nonroot@sha256:55716e80a7d4320ce9bc2dc8636fc193b418638041b817cf3306696bd0f975d1
LABEL org.opencontainers.image.url='https://github.com/srinandan/building-permit/api' \
    org.opencontainers.image.documentation='https://github.com/srinandan/building-permit/api' \
    org.opencontainers.image.source='https://github.com/srinandan/building-permit/api' \
    org.opencontainers.image.vendor='Google LLC' \
    org.opencontainers.image.licenses='Apache-2.0'

COPY --from=build /app/api-server /usr/local/bin/api-server
EXPOSE 8080
ENV PORT=8080
ENV DB_NAME=/app/data/building_plans.db
ENV OTEL_SERVICE_NAME=building-permit-api
ENV OTEL_TRACES_EXPORTER=otlp
ENV OTEL_EXPORTER_OTLP_ENDPOINT=https://telemetry.googleapis.com
# Create a volume for the sqlite database to persist
VOLUME ["/app/data"]
ENTRYPOINT ["api-server"]
