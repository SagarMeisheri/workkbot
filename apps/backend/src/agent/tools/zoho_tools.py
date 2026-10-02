"""Google ADK 2.0 Zoho India Managed Auth & Browser Tools (Spec 11).

Defines Google ADK 2.0 BaseTools for:
1. zoho_india_login: Initiates Kernel Managed Auth login flow for Zoho India (.in data residency)
   and creates a persistent authenticated browser profile.
2. zoho_browse_authenticated: Spawns an authenticated cloud browser with the Zoho profile
   already logged in, navigating directly to Zoho Books, Zoho CRM, or Zoho Invoices.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from src.vm.zoho_browser import ZohoIndiaBrowserRunner, zoho_browser_runner

logger = logging.getLogger("workkbot.zoho_tools")

ZOHO_LOGIN_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "profile_name": {
            "type": "string",
            "description": "Identifier for the persistent browser profile (defaults to 'zoho-india-profile').",
        },
    },
}

ZOHO_BROWSE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "url": {
            "type": "string",
            "description": "Target Zoho India URL to access (e.g., 'https://books.zoho.in', 'https://accounts.zoho.in', 'https://invoice.zoho.in').",
        },
        "profile_name": {
            "type": "string",
            "description": "The profile name storing authenticated session state (defaults to 'zoho-india-profile').",
        },
    },
}

try:
    from google.adk.tools import BaseTool
    from google.genai import types

    class ZohoIndiaLoginTool(BaseTool):
        """Google ADK 2.0 tool for initiating Zoho India Managed Auth login."""

        def __init__(self, runner: Optional[ZohoIndiaBrowserRunner] = None):
            super().__init__(
                name="zoho_india_login",
                description="Initiates Zoho India (.in) Managed Auth login. Creates a reusable authenticated profile and returns the login URL.",
            )
            self.runner = runner or zoho_browser_runner

        def _get_declaration(self) -> Optional[types.FunctionDeclaration]:
            return types.FunctionDeclaration(
                name=self.name,
                description=self.description,
                parameters_json_schema=ZOHO_LOGIN_SCHEMA,
            )

        async def run_async(self, *, args: Dict[str, Any], tool_context: Any = None) -> Any:
            profile_name = args.get("profile_name", "zoho-india-profile")
            logger.info("Running zoho_india_login for profile: %s", profile_name)
            result = await self.runner.initiate_login(profile_name=profile_name)

            hosted_url = result.get("hosted_url")
            summary = (
                f"Zoho India Managed Auth connection created for profile '{profile_name}'.\n"
                f"Please open the following link to authenticate your Zoho account:\n"
                f"{hosted_url}\n\n"
                "Once logged in, your authenticated session is securely persisted to the profile for autonomous browsing."
            )
            return {
                "status": "success",
                "summary": summary,
                "profile_name": profile_name,
                "hosted_url": hosted_url,
                "live_view_url": result.get("live_view_url"),
                "connection_id": result.get("connection_id"),
            }

    class ZohoBrowseAuthenticatedTool(BaseTool):
        """Google ADK 2.0 tool for navigating Zoho India with saved profile authentication."""

        def __init__(self, runner: Optional[ZohoIndiaBrowserRunner] = None):
            super().__init__(
                name="zoho_browse_authenticated",
                description="Navigates to Zoho India applications (e.g. books.zoho.in, invoice.zoho.in) using a pre-authenticated profile.",
            )
            self.runner = runner or zoho_browser_runner

        def _get_declaration(self) -> Optional[types.FunctionDeclaration]:
            return types.FunctionDeclaration(
                name=self.name,
                description=self.description,
                parameters_json_schema=ZOHO_BROWSE_SCHEMA,
            )

        async def run_async(self, *, args: Dict[str, Any], tool_context: Any = None) -> Any:
            url = args.get("url", "https://books.zoho.in")
            profile_name = args.get("profile_name", "zoho-india-profile")
            logger.info("Running zoho_browse_authenticated: url=%s, profile=%s", url, profile_name)

            result = await self.runner.open_authenticated_session(
                target_url=url,
                profile_name=profile_name,
            )

            if result.get("status") == "success":
                summary = (
                    f"Successfully loaded authenticated Zoho India session at {url}.\n"
                    f"Page Title: {result.get('title', 'N/A')}\n"
                    f"Session ID: {result.get('session_id')}"
                )
            else:
                summary = f"Could not load authenticated Zoho session: {result.get('error')}"

            return {
                "status": result.get("status"),
                "summary": summary,
                "current_url": result.get("current_url"),
                "session_id": result.get("session_id"),
                "live_view_url": result.get("live_view_url"),
                "dom_snapshot": result.get("dom_snapshot"),
                "error": result.get("error"),
            }

    zoho_login_tool = ZohoIndiaLoginTool()
    zoho_browse_tool = ZohoBrowseAuthenticatedTool()

except ImportError:
    class ZohoIndiaLoginTool:  # type: ignore
        def __init__(self, runner: Optional[ZohoIndiaBrowserRunner] = None):
            self.name = "zoho_india_login"
            self.description = "Initiates Zoho India (.in) Managed Auth login."
            self.runner = runner or zoho_browser_runner

        async def run_async(self, *, args: Dict[str, Any], tool_context: Any = None) -> Any:
            return await self.runner.initiate_login(profile_name=args.get("profile_name", "zoho-india-profile"))

    class ZohoBrowseAuthenticatedTool:  # type: ignore
        def __init__(self, runner: Optional[ZohoIndiaBrowserRunner] = None):
            self.name = "zoho_browse_authenticated"
            self.description = "Navigates to Zoho India applications using pre-authenticated profile."
            self.runner = runner or zoho_browser_runner

        async def run_async(self, *, args: Dict[str, Any], tool_context: Any = None) -> Any:
            return await self.runner.open_authenticated_session(
                target_url=args.get("url", "https://books.zoho.in"),
                profile_name=args.get("profile_name", "zoho-india-profile"),
            )

    zoho_login_tool = ZohoIndiaLoginTool()
    zoho_browse_tool = ZohoBrowseAuthenticatedTool()
