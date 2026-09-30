"""MCP Tool Parameter Sanitizer (CVE-2026-29791 & Spec 04, R04.2).

Recursively inspects and sanitizes tool arguments to prevent path traversal,
shell delimiter injections, and CRLF parameter tampering.
"""
import re
from typing import Any, Dict, List, Union

# Forbidden patterns indicating parameter tampering
PATH_TRAVERSAL_PATTERN = re.compile(r"(\.\./|\.\.\\|%2e%2e%2f|%2e%2e/)", re.IGNORECASE)
SHELL_METACHRACTERS_PATTERN = re.compile(r"(\$\(.*\)|`.*`|[;&|><])")
CRLF_PATTERN = re.compile(r"[\r\n]")
NULL_BYTE_PATTERN = re.compile(r"\x00")


class ParameterSanitizerError(ValueError):
    """Raised when dangerous parameter injection is detected."""
    pass


class ParameterSanitizer:
    """Validates and sanitizes dynamic MCP tool arguments."""

    def sanitize_string(self, value: str, field_name: str = "") -> str:
        """Validates a string value against injection patterns."""
        if NULL_BYTE_PATTERN.search(value):
            raise ParameterSanitizerError(f"Null byte detected in argument '{field_name}'")

        if PATH_TRAVERSAL_PATTERN.search(value):
            raise ParameterSanitizerError(f"Path traversal detected in argument '{field_name}': '{value}'")

        if SHELL_METACHRACTERS_PATTERN.search(value):
            raise ParameterSanitizerError(f"Shell metacharacters detected in argument '{field_name}'")

        MULTILINE_FIELDS = (
            "_body", "_content", "_text", "_description", "_summary", "_notes", "_message",
            "body", "content", "text", "description", "summary", "notes", "message",
        )
        is_multiline_field = field_name.lower().endswith(MULTILINE_FIELDS)

        # Strip unescaped carriage returns and line feeds in single-line fields (VULN-08 Defense)
        if ("\r" in value or "\n" in value) and not is_multiline_field:
            cleaned = CRLF_PATTERN.sub(" ", value)
        else:
            cleaned = value
        return cleaned

    def sanitize_arguments(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively inspects a dictionary of tool arguments."""
        sanitized: Dict[str, Any] = {}
        for key, val in args.items():
            sanitized[key] = self._sanitize_value(val, field_name=key)
        return sanitized

    def _sanitize_value(self, val: Any, field_name: str) -> Any:
        if isinstance(val, str):
            return self.sanitize_string(val, field_name=field_name)
        elif isinstance(val, dict):
            return {k: self._sanitize_value(v, field_name=f"{field_name}.{k}") for k, v in val.items()}
        elif isinstance(val, list):
            return [self._sanitize_value(item, field_name=f"{field_name}[]") for item in val]
        return val


parameter_sanitizer = ParameterSanitizer()
