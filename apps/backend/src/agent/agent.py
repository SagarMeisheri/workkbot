"""Google ADK 2.0 Core Agent Definition (Spec 02, R02.1).

Defines the canonical LlmAgent(name="workkbot_core") using Google ADK 2.0 (google-adk).
Configured with enterprise Indian SMB system instructions, Gemini reasoning, and tools.
"""
from typing import List, Optional
from src.config import settings

WORKKBOT_SYSTEM_INSTRUCTION = """You are Workkbot, an intelligent enterprise AI assistant.

Your core operating standards:
1. Deliver concise, actionable, and accurate responses tailored to the user's workflow.
2. Strictly respect user data privacy, confidentiality, and data protection principles.
3. Format responses cleanly in markdown with structured headings, tables, bullet points, and code snippets where appropriate.
4. Provide transparent reasoning and clear explanations for complex queries.

CONSTRAINT & TOOL EXECUTION BUDGET:
- You are strictly allowed a maximum of 2 tool calls per user turn.
- If you call a tool and receive its result, immediately formulate your final answer. Do NOT loop repeatedly or re-query with variations.
- If you cannot find what you are looking for after 1 or 2 tool calls, stop immediately and report the exact results or status to the user.

FACTUAL INTEGRITY & ZERO HALLUCINATION POLICY:
- If a tool returns no results, 0 items, or indicates that an automated browser search found no live options, you MUST report that fact honestly to the user.
- You must NEVER fabricate, hallucinate, or estimate flight prices, airlines, flight numbers, or timings. State clearly that the automated search returned no live pricing data.
"""

try:
    from google.adk import Agent
    from google.adk.agents import LlmAgent
    from src.compliance.callbacks import (
        pii_anonymize_callback,
        tool_rehydration_callback,
        tool_output_mask_callback,
    )
    from src.mcp.tools import dynamic_mcp_toolset
    from src.agent.tools.flight_tools import flight_tool

    # Canonical Google ADK 2.0 LlmAgent instance with dynamic MCP toolset and autonomous browser tools
    root_agent = Agent(
        name="workkbot_core",
        model=settings.DEFAULT_MODEL,
        description="Intelligent enterprise AI assistant.",
        instruction=WORKKBOT_SYSTEM_INSTRUCTION,
        tools=[dynamic_mcp_toolset, flight_tool],
        before_model_callback=pii_anonymize_callback,
        before_tool_callback=tool_rehydration_callback,
        after_tool_callback=tool_output_mask_callback,
    )
except ImportError:
    from src.agent.tools.flight_tools import flight_tool

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
        tools=[flight_tool],
    )

# Canonical exports
core_agent = root_agent
agent = root_agent
