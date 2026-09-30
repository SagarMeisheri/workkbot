"""MCP Parameter Sanitizer & CVE-2026-29791 Immunity (Spec 04, R04.2).

Guarantees deep parameter sanitization on all dynamic tool inputs:
- Blocks path traversal (../, ..\\)
- Neutralizes CRLF injection (\\r, \\n)
- Strips shell metacharacters (; & | ` $ > <)
- Recursively sanitizes primitive values, lists, and nested dictionaries
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Union


class McpParameterSanitizer:
    """Sanitizes tool call parameters to defend against parameter tampering and injection."""

    # Shell characters forbidden in dynamic arguments
    SHELL_METACHAR_PATTERN = re.compile(r"[;&|`$><]")

    @classmethod
    def sanitize_string(cls, value: str) -> str:
        """Sanitizes an individual string value."""
        if not isinstance(value, str):
            return value

        # 1. Neutralize CRLF injection
        cleaned = value.replace("\r", " ").replace("\n", " ")

        # 2. Strip path traversal sequences repeatedly until none remain
        while ".." in cleaned:
            cleaned = cleaned.replace("../", "").replace("..\\", "").replace("..", "")

        # 3. Strip shell metacharacters
        cleaned = cls.SHELL_METACHAR_PATTERN.sub("", cleaned)

        return cleaned.strip()

    @classmethod
    def sanitize_arguments(cls, args: Any) -> Any:
        """Recursively sanitizes parameter arguments across primitives, dicts, and lists."""
        if isinstance(args, str):
            return cls.sanitize_string(args)
        elif isinstance(args, dict):
            return {
                cls.sanitize_string(k) if isinstance(k, str) else k: cls.sanitize_arguments(v)
                for k, v in args.items()
            }
        elif isinstance(args, list):
            return [cls.sanitize_arguments(item) for item in args]
        elif isinstance(args, (int, float, bool)) or args is None:
            return args
        else:
            return cls.sanitize_string(str(args))


mcp_sanitizer = McpParameterSanitizer()
