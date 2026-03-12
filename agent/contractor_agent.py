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

import os
from google.adk.agents import LlmAgent
from google.adk.tools import google_search

def create_contractor_agent(model_name: str) -> LlmAgent:
    """Creates an ADK LlmAgent configured to find licensed contractors."""

    system_instruction = """
    You are an expert at finding licensed contractors for specific jobs in a given area.
    Use the google_search tool to find real, highly-rated, licensed contractors that match the user's needs.
    Always provide contact information, a brief description of the contractor, and why they are a good fit for the job.
    If the user asks for contractors in a specific area (like Santa Clara County), focus your search there.
    """

    agent = LlmAgent(
        name="contractor_agent",
        model=model_name,
        instruction=system_instruction,
        tools=[google_search]
    )

    return agent
