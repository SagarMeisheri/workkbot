"""Agentgateway 1.5.x Client & Anti-Poisoning Filter (Spec 04, R04.2).

Interfaces with the in-pod Rust Agentgateway on loopback (127.0.0.1:8080/mcp),
filters out prompt injection markers from external tool definitions,
and prevents tool shadowing attacks against core system tools.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Callable, Dict, List, Optional

import httpx

from src.mcp.sanitizer import mcp_sanitizer

logger = logging.getLogger("workkbot.mcp.client")


class AntiPoisoningFilter:
    """Detects and strips adversarial prompt injection delimiters from tool descriptions."""

    DISALLOWED_PATTERNS = [
        r"system:\s*",
        r"assistant:\s*",
        r"SYSTEM OVERRIDE:?",
        r"<instructions>.*?</instructions>",
        r"<instructions>",
        r"</instructions>",
        r"<\|im_start\|>",
        r"<\|im_end\|>",
        r"\[INST\]",
        r"\[/INST\]",
        r"IGNORE ALL PREVIOUS INSTRUCTIONS",
    ]

    @classmethod
    def sanitize_description(cls, description: str, max_tokens: int = 512) -> str:
        """Strips injection delimiters and safely truncates length."""
        if not description:
            return ""

        cleaned = description
        for pattern in cls.DISALLOWED_PATTERNS:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE | re.DOTALL)

        # Collapse excessive whitespace
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # Enforce maximum token limit (approximated by word count)
        words = cleaned.split()
        if len(words) > max_tokens:
            cleaned = " ".join(words[:max_tokens])

        return cleaned

    @classmethod
    def is_poisoned(cls, text: str) -> bool:
        """Returns True if the text contains adversarial prompt injection markers."""
        if not text:
            return False
        for pattern in cls.DISALLOWED_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                return True
        return False


class AgentgatewayMcpClient:
    """Client for Agentgateway federated MCP proxy on loopback."""

    CORE_SYSTEM_TOOLS = {
        "workkbot_core",
        "workkbot_gst_lookup",
        "workkbot_compliance_audit",
        "chat_stream",
        "session_service",
    }

    def __init__(self, base_url: str = "http://127.0.0.1:8080/mcp"):
        self.base_url = base_url
        self._mock_servers: Dict[str, List[Dict[str, Any]]] = {}

    def register_mock_server(self, provider: str, tools: List[Dict[str, Any]]) -> None:
        """Registers in-memory tools for local testing without external daemon."""
        self._mock_servers[provider] = tools

    async def list_tools(self, provider: Optional[str] = None) -> List[Dict[str, Any]]:
        """Discovers tools across federated MCP upstreams with anti-poisoning sanitization."""
        tools: List[Dict[str, Any]] = []

        if provider and provider in self._mock_servers:
            raw_tools = self._mock_servers[provider]
            for t in raw_tools:
                sanitized = dict(t)
                sanitized["description"] = AntiPoisoningFilter.sanitize_description(
                    t.get("description", "")
                )
                tools.append(sanitized)
            return tools

        if not self._mock_servers:
            # Query live Agentgateway on loopback
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    resp = await client.post(
                        f"{self.base_url}/tools/list",
                        json={"provider": provider} if provider else {},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        for t in data.get("tools", []):
                            t["description"] = AntiPoisoningFilter.sanitize_description(
                                t.get("description", "")
                            )
                            tools.append(t)
            except Exception as e:
                logger.debug("Agentgateway loopback connection fallback: %s", e)

        for s_tools in self._mock_servers.values():
            for t in s_tools:
                sanitized = dict(t)
                sanitized["description"] = AntiPoisoningFilter.sanitize_description(
                    t.get("description", "")
                )
                tools.append(sanitized)

        return tools

    def check_tool_shadowing(self, tool_name: str) -> bool:
        """Returns True if the tool name illegally shadows a core system tool."""
        return tool_name.lower() in self.CORE_SYSTEM_TOOLS

    async def execute_tool(
        self,
        provider: str,
        tool_name: str,
        arguments: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Executes a tool on Agentgateway or mock server with sanitized arguments."""
        if self.check_tool_shadowing(tool_name):
            raise ValueError(f"Security violation: tool '{tool_name}' shadows a core system tool")

        sanitized_args = mcp_sanitizer.sanitize_arguments(arguments)

        # Check mock server handlers
        if provider in self._mock_servers:
            for t in self._mock_servers[provider]:
                if t.get("name") == tool_name:
                    handler = t.get("handler")
                    if handler:
                        if callable(handler):
                            import inspect

                            if inspect.iscoroutinefunction(handler):
                                return await handler(sanitized_args)
                            return handler(sanitized_args)
                    return {"status": "success", "result": f"Executed {tool_name}"}

        # Call live Agentgateway
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self.base_url}/tools/execute",
                    json={
                        "provider": provider,
                        "tool": tool_name,
                        "arguments": sanitized_args,
                    },
                    headers=headers or {},
                )
                if resp.status_code == 200:
                    return resp.json()
                return {
                    "status": "failed",
                    "error": f"Agentgateway error {resp.status_code}: {resp.text}",
                }
        except Exception as e:
            return {"status": "failed", "error": f"Connection error to Agentgateway: {e}"}


agentgateway_client = AgentgatewayMcpClient()
