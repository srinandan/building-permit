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

FROM node:20-alpine
LABEL org.opencontainers.image.url='https://github.com/srinandan/building-permit/frontend' \
    org.opencontainers.image.documentation='https://github.com/srinandan/building-permit/frontend' \
    org.opencontainers.image.source='https://github.com/srinandan/building-permit/frontend' \
    org.opencontainers.image.vendor='Google LLC' \
    org.opencontainers.image.licenses='Apache-2.0'
WORKDIR /app

# OpenTelemetry Configuration
ARG PROJECT_ID
ENV VITE_PROJECT_ID=$PROJECT_ID

ARG API_KEY
ENV VITE_OTLP_API_KEY=$API_KEY

ENV OTEL_SERVICE_NAME=building-permit-frontend
ENV OTEL_TRACES_EXPORTER=otlp
ENV OTEL_EXPORTER_OTLP_ENDPOINT=https://telemetry.googleapis.com
ENV VITE_OTLP_EXPORTER_URL=https://telemetry.googleapis.com/v1/traces


# Copy package files and install all dependencies (including devDependencies for the build)
COPY package*.json ./
RUN npm install

# Copy source code and build the React application
COPY . .
RUN npm run build

# Expose port 3000 (which server.js uses by default)
EXPOSE 8080

ENV PORT=8080

# Start the Express server
CMD ["node", "server.js"]
