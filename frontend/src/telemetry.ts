/**
 * Copyright 2026 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { WebTracerProvider } from '@opentelemetry/sdk-trace-web';
import { BatchSpanProcessor } from '@opentelemetry/sdk-trace-base';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { registerInstrumentations } from '@opentelemetry/instrumentation';
import { DocumentLoadInstrumentation } from '@opentelemetry/instrumentation-document-load';
import { XMLHttpRequestInstrumentation } from '@opentelemetry/instrumentation-xml-http-request';
import { FetchInstrumentation } from '@opentelemetry/instrumentation-fetch';
import { ZoneContextManager } from '@opentelemetry/context-zone';
import { ATTR_SERVICE_NAME } from '@opentelemetry/semantic-conventions';
import { resourceFromAttributes } from '@opentelemetry/resources';

export function initTelemetry() {
  let url = import.meta.env.VITE_OTLP_EXPORTER_URL;
  if (url && !url.endsWith('/v1/traces')) {
    url += '/v1/traces';
  }

  const headers: Record<string, string> = {};
  if (import.meta.env.VITE_OTLP_API_KEY) {
    headers['x-goog-api-key'] = import.meta.env.VITE_OTLP_API_KEY;
  }

  const exporter = new OTLPTraceExporter({
    url: url || '/v1/traces', // Default to relative path which hits our server.js proxy
    headers: headers,
  });

  const resource = resourceFromAttributes({
    [ATTR_SERVICE_NAME]: 'building-permit-frontend',
    'gcp.project_id': import.meta.env.VITE_PROJECT_ID,
  });

  const provider = new WebTracerProvider({
    resource: resource,
    spanProcessors: [new BatchSpanProcessor(exporter)],
  });

  provider.register({
    contextManager: new ZoneContextManager(),
  });

  registerInstrumentations({
    instrumentations: [
      new DocumentLoadInstrumentation(),
      new XMLHttpRequestInstrumentation({
        propagateTraceHeaderCorsUrls: [/.+/g], // Propagate context to all domains
      }),
      new FetchInstrumentation({
        propagateTraceHeaderCorsUrls: [/.+/g],
      }),
    ],
  });

  console.log('OpenTelemetry initialized for frontend');
}
