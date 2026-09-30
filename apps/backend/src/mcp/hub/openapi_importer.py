"""OpenAPI 3.0 to MCP Virtualizer & Schema Compiler (Spec 05, R05.2 & VAL-05.2).

Converts Indian ERP and SMB REST API definitions (OpenAPI 3.0 / Swagger) into native MCP tools:
- Compiles paths, methods, parameters, and request bodies into JSONSchema declarations.
- Flags mutating HTTP verbs (POST, PUT, DELETE, PATCH) as critical for HITL confirmation.
- Employs AntiSsrfValidator before fetching remote OpenAPI specification URLs.
- Enforces parameter sanitization (CVE-2026-29791) on virtualized tools.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional
import httpx

from src.mcp.classifier import tool_classifier
from src.mcp.hub.ssrf_validator import ssrf_validator

logger = logging.getLogger("workkbot.mcp.openapi")


class OpenApiVirtualizationError(ValueError):
    """Raised when OpenAPI spec is invalid or cannot be parsed."""
    pass


class OpenApiImporter:
    """Virtualizes OpenAPI 3.0 / Swagger JSON definitions into native MCP tools."""

    @classmethod
    def _sanitize_tool_name(cls, raw_name: str) -> str:
        """Converts raw operationId or path into clean snake_case identifier."""
        name = re.sub(r"[^a-zA-Z0-9_]+", "_", raw_name.strip()).strip("_").lower()
        if not name or name[0].isdigit():
            name = f"op_{name}"
        return name

    @classmethod
    def parse_openapi_spec(
        cls,
        spec: Dict[str, Any],
        provider_name: str = "openapi_custom",
    ) -> List[Dict[str, Any]]:
        """
        Parses OpenAPI 3.0 / Swagger dictionary and extracts MCP tool definitions.
        """
        if not isinstance(spec, dict):
            raise OpenApiVirtualizationError("OpenAPI specification must be a JSON object")

        paths = spec.get("paths", {})
        if not paths or not isinstance(paths, dict):
            raise OpenApiVirtualizationError("OpenAPI specification contains no paths")

        mcp_tools: List[Dict[str, Any]] = []

        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            for method in ("get", "post", "put", "delete", "patch"):
                op = path_item.get(method)
                if not op or not isinstance(op, dict):
                    continue

                operation_id = op.get("operationId")
                summary = op.get("summary") or op.get("description") or f"{method.upper()} {path}"

                # Generate clean tool name
                if operation_id:
                    tool_name = cls._sanitize_tool_name(operation_id)
                else:
                    path_clean = cls._sanitize_tool_name(path)
                    tool_name = f"{method}_{path_clean}"

                # Build JSONSchema for parameters
                properties: Dict[str, Any] = {}
                required: List[str] = []

                # 1. Path and Query Parameters
                parameters = op.get("parameters", [])
                if isinstance(parameters, list):
                    for param in parameters:
                        if not isinstance(param, dict):
                            continue
                        p_name = param.get("name")
                        if not p_name:
                            continue
                        p_schema = param.get("schema", {"type": "string"})
                        p_desc = param.get("description", f"Parameter {p_name}")
                        properties[p_name] = {
                            "type": p_schema.get("type", "string"),
                            "description": p_desc,
                        }
                        if param.get("required"):
                            required.append(p_name)

                # 2. Request Body Properties (OpenAPI 3.0)
                req_body = op.get("requestBody", {})
                if isinstance(req_body, dict):
                    content = req_body.get("content", {})
                    app_json = content.get("application/json", {})
                    body_schema = app_json.get("schema", {})
                    if isinstance(body_schema, dict) and "properties" in body_schema:
                        for b_name, b_prop in body_schema["properties"].items():
                            if isinstance(b_prop, dict):
                                properties[b_name] = b_prop
                        if "required" in body_schema and isinstance(body_schema["required"], list):
                            required.extend(body_schema["required"])

                input_schema = {
                    "type": "object",
                    "properties": properties,
                    "required": list(set(required)),
                }

                # Mutating HTTP methods are critical
                is_method_mutating = method in ("post", "put", "delete", "patch")
                is_critical = is_method_mutating or tool_classifier.is_critical(
                    tool_name=tool_name,
                    description=summary,
                    parameters_schema=input_schema,
                )

                mcp_tools.append({
                    "name": tool_name,
                    "provider": provider_name,
                    "description": summary,
                    "method": method.upper(),
                    "path": path,
                    "inputSchema": input_schema,
                    "parameters_schema": input_schema,
                    "critical": is_critical,
                    "requires_hitl": is_critical,
                })

        return mcp_tools

    @classmethod
    async def import_from_url(
        cls,
        spec_url: str,
        provider_name: str = "openapi_custom",
    ) -> List[Dict[str, Any]]:
        """
        Fetches remote OpenAPI spec after deep SSRF verification (CVE-2026-31943)
        and parses tools into MCP format.
        """
        # 1. Anti-SSRF and DNS Rebinding check
        ssrf_validator.assert_safe_url(spec_url)

        # 2. Fetch spec with redirects disabled (disallow redirect-based SSRF)
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=False) as client:
            res = await client.get(spec_url)
            if res.status_code != 200:
                raise OpenApiVirtualizationError(f"HTTP {res.status_code} error fetching OpenAPI spec: {res.text[:200]}")
            spec_data = res.json()

        return cls.parse_openapi_spec(spec_data, provider_name)


openapi_importer = OpenApiImporter
