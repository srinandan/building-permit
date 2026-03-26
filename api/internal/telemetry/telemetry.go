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

package telemetry

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"os"

	texporter "github.com/GoogleCloudPlatform/opentelemetry-operations-go/exporter/trace"
	"go.opentelemetry.io/contrib/detectors/gcp"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/contrib/propagators/autoprop"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.24.0"
	"go.opentelemetry.io/otel/trace"

)

// InitTelemetry initializes OpenTelemetry for Tracing and Metrics using Google Cloud exporters.
// It returns a shutdown function that should be called on service exit.
func InitTelemetry(ctx context.Context, projectID, location, serviceName string) (func(context.Context) error, error) {
	var shutdownFuncs []func(context.Context) error

	// shutdown combines shutdown functions from multiple OpenTelemetry
	// components into a single function.
	shutdown := func(ctx context.Context) error {
		var err error
		for _, fn := range shutdownFuncs {
			err = errors.Join(err, fn(ctx))
		}
		shutdownFuncs = nil
		return err
	}

	// Define resource attributes
	res, err := resource.New(ctx,
		resource.WithDetectors(gcp.NewDetector()),
		resource.WithTelemetrySDK(),
		resource.WithAttributes(
			semconv.ServiceNameKey.String(serviceName),
			attribute.String("gcp.project_id", projectID),
			attribute.String("gcp.location", location),
			attribute.String("cloud.provider", "gcp"),
			attribute.String("cloud.region", location),
			attribute.String("cloud.account.id", projectID),
		),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create resource: %w", err)
	}

	traceExporter, err := texporter.New(texporter.WithProjectID(projectID))
	if err != nil {
		return nil, fmt.Errorf("failed to create GCP trace exporter: %w", err)
	}

	tp := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(traceExporter),
		sdktrace.WithResource(res),
		sdktrace.WithSampler(sdktrace.AlwaysSample()),
	)
	shutdownFuncs = append(shutdownFuncs, tp.Shutdown)
	otel.SetTracerProvider(tp)

	// 3. Propagator
	otel.SetTextMapPropagator(autoprop.NewTextMapPropagator())

	// 4. Logger Setup (slog with Trace Context)
	initSlog(projectID)

	return shutdown, nil
}

// initSlog configures the default slog logger to output JSON to stdout
// and include trace/span IDs in the format Google Cloud Logging expects.
func initSlog(projectID string) {
	handler := &ContextHandler{
		Handler: slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
			Level: slog.LevelInfo,
		}),
		ProjectID: projectID,
	}
	logger := slog.New(handler)
	slog.SetDefault(logger)
}

// ContextHandler wraps a slog.Handler to add trace information from the context.
type ContextHandler struct {
	slog.Handler
	ProjectID string
}

// Handle adds the trace_id and span_id to the record if present in the context.
func (h *ContextHandler) Handle(ctx context.Context, r slog.Record) error {
	span := trace.SpanFromContext(ctx)
	if span.SpanContext().IsValid() {
		// Google Cloud Logging expects:
		// "logging.googleapis.com/trace": "projects/[PROJECT_ID]/traces/[TRACE_ID]"
		// "logging.googleapis.com/spanId": "[SPAN_ID]"
		// "logging.googleapis.com/trace_sampled": true/false

		traceID := span.SpanContext().TraceID().String()
		spanID := span.SpanContext().SpanID().String()

		traceField := fmt.Sprintf("projects/%s/traces/%s", h.ProjectID, traceID)
		r.AddAttrs(
			slog.String("logging.googleapis.com/trace", traceField),
			slog.String("logging.googleapis.com/spanId", spanID),
			slog.Bool("logging.googleapis.com/trace_sampled", span.SpanContext().IsSampled()),
		)
	}
	return h.Handler.Handle(ctx, r)
}
