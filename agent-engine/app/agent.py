from google.adk.agents import LlmAgent

app = LlmAgent(
    name="building_permit_agent",
    model="gemini-2.5-pro",
    instruction="You are a helpful building permit proxy agent."
)
