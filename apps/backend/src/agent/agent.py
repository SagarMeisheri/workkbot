"""Google ADK 2.0 Core Agent Definition (Spec 02, R02.1).

Defines the canonical LlmAgent(name="workkbot_core") using Google ADK 2.0 (google-adk).
Configured with enterprise Indian SMB system instructions, Gemini reasoning, and tools.
"""
from typing import List, Optional
from src.config import settings

WORKKBOT_SYSTEM_INSTRUCTION = """You are Workkbot 2.0, the sovereign AI enterprise coworker for Indian SMBs and global teams.
You operate under the 5 Core Frameworks Architecture (Supabase, GCP asia-south1, Google ADK 2.0, assistant-ui, Agentgateway).

Your core operating standards:
1. Deliver concise, actionable, and accurate corporate insights.
2. Specialize in Indian business operations including GST compliance, Zoho Workplace, Tally Prime integration, and Google Workspace workflows.
3. Strictly respect user privacy and statutory compliance under the India Digital Personal Data Protection (DPDP) Act 2023.
4. Format responses cleanly in markdown with tables, bullet points, and code snippets where appropriate.
5. Provide transparent reasoning thoughts for complex queries when requested.
"""

try:
    from google.adk import Agent
    from google.adk.agents import LlmAgent
    from src.compliance.callbacks import (
        pii_anonymize_callback,
        tool_rehydration_callback,
        tool_output_mask_callback,
    )

    # Canonical Google ADK 2.0 LlmAgent instance
    root_agent = Agent(
        name="workkbot_core",
        model=settings.DEFAULT_MODEL,
        description="Sovereign AI enterprise coworker for Indian SMBs and global teams.",
        instruction=WORKKBOT_SYSTEM_INSTRUCTION,
        tools=[],
        before_model_callback=pii_anonymize_callback,
        before_tool_callback=tool_rehydration_callback,
        after_tool_callback=tool_output_mask_callback,
    )
except ImportError:
    # Fallback definition when google-adk is not yet synced in local runner
    class _LlmAgentFallback:
        def __init__(
            self,
            name: str = "workkbot_core",
            model: str = settings.DEFAULT_MODEL,
            description: str = "",
            instruction: str = "",
            tools: Optional[List] = None,
        ):
            self.name = name
            self.model = model
            self.description = description
            self.instruction = instruction
            self.tools = tools or []

        def get_system_prompt(self) -> str:
            return self.instruction

    root_agent = _LlmAgentFallback(
        name="workkbot_core",
        model=settings.DEFAULT_MODEL,
        description="Sovereign AI enterprise coworker for Indian SMBs and global teams.",
        instruction=WORKKBOT_SYSTEM_INSTRUCTION,
        tools=[],
    )

# Canonical exports
core_agent = root_agent
agent = root_agent
