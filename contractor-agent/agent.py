# ruff: noqa
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

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools import google_search
from google.genai import types
import os
import google.auth

_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")

root_agent = Agent(
    name="ContractorAgent",
    model=Gemini(
        model=model_name,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    description="Finds licensed contractors for specific jobs.",
    instruction="""
    You are an expert at finding licensed contractors for specific jobs in a given area.
    Use the google_search tool to find real, highly-rated, licensed contractors that match the user's needs.
    Always provide contact information, a brief description of the contractor, and why they are a good fit for the job.
    If the user asks for contractors in a specific area (like San Paloma County), focus your search there.
    """,
    tools=[google_search],
)

app = App(
    root_agent=root_agent,
    name="contractor_agent",
)
