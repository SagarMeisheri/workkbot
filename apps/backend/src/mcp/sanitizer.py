"""MCP Parameter Sanitizer defending against CVE-2026-29791 (Spec 04, R04.2).

Guarantees that dynamic tool arguments passed to Agentgateway or upstream tools:
- Cannot perform directory traversal (../, ..\\, %2e%2e).
- Cannot inject carriage return / line feed (CRLF) for header smuggling.
- Cannot inject shell metacharacters (;, &, |, `, $, >, <) into execution environments.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple, Union

# Patterns for CVE-2026-29791 parameter injection
TRAVERSAL_PATTERN = re.compile(r"(\.\./|\.\.\\|%2e%2e[/\\%]|%252e%252e)", re.IGNORECASE)
CRLF_PATTERN = re.compile(r"[\r\n]+")
SHELL_META_PATTERN = re.compile(r"[;&|`$><]")


class ParameterSanitizationError(ValueError):
    """Raised when an argument contains dangerous or un-sanitizable characters."""
    pass


class McpParameterSanitizer:
    """Sanitizes dynamic tool parameters recursively."""

    @classmethod
    def sanitize_string(cls, val: str, strict: bool = False) -> str:
        """
        Sanitizes a single string value:
        - Removes path traversal markers
        - Removes CRLF
        - Removes or escapes shell metacharacters
        """
        if not val or not isinstance(val, str):
            return val

        # Check for path traversal attempts (including recursive/nested attacks)
        if TRAVERSAL_PATTERN.search(val) or ".." in val:
            if strict:
                raise ParameterSanitizationError(f"Path traversal detected in argument: {val}")
            for _ in range(10):
                prev = val
                val = TRAVERSAL_PATTERN.sub("", val)
                val = val.replace("..", "")
                if val == prev:
                    break

        # Check for CRLF injection
        if CRLF_PATTERN.search(val):
            if strict:
                raise ParameterSanitizationError("CRLF injection detected in argument")
            val = CRLF_PATTERN.sub(" ", val)

        # Check for shell metacharacters
        if SHELL_META_PATTERN.search(val):
            if strict:
                raise ParameterSanitizationError("Shell metacharacters detected in argument")
            val = SHELL_META_PATTERN.sub("", val)

        return val.strip()

    @classmethod
    def sanitize_arguments(
        cls,
        args: Dict[str, Any],
        strict: bool = False,
    ) -> Dict[str, Any]:
        """
        Recursively sanitizes a dictionary of tool arguments.
        """
        if not isinstance(args, dict):
            return args

        sanitized: Dict[str, Any] = {}
        for key, value in args.items():
            # Sanitize parameter key itself
            clean_key = cls.sanitize_string(key, strict=strict)

            if isinstance(value, str):
                sanitized[clean_key] = cls.sanitize_string(value, strict=strict)
            elif isinstance(value, dict):
                sanitized[clean_key] = cls.sanitize_arguments(value, strict=strict)
            elif isinstance(value, list):
                sanitized[clean_key] = [
                    cls.sanitize_string(item, strict=strict) if isinstance(item, str)
                    else cls.sanitize_arguments(item, strict=strict) if isinstance(item, dict)
                    else item
                    for item in value
                ]
            else:
                sanitized[clean_key] = value

        return sanitized

    @classmethod
    def validate_safe(cls, args: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validates whether parameters are 100% clean without mutating them.
        Returns (is_safe, error_reason).
        """
        try:
            cls.sanitize_arguments(args, strict=True)
            return True, None
        except ParameterSanitizationError as e:
            return False, str(e)


mcp_sanitizer = McpParameterSanitizer
