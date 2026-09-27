"""
Workkbot Local PoC: Client-Side Connected OAuth Vault
Manages Google Workspace & Zoho Suite credentials client-side.
Provides automatic token refresh, authorization code exchange, and live token retrieval.
"""
from dataclasses import dataclass, field
import datetime
import json
import os
from typing import Any, Dict, Optional
from src.mcp.oauth_engine import OAuthManager


@dataclass
class GoogleOAuthState:
    connected: bool = False
    client_id: str = ""
    client_secret: str = ""
    redirect_uri: str = "http://localhost:8501"
    access_token: str = ""
    refresh_token: str = ""
    expires_at: Optional[str] = None
    scopes: list = field(default_factory=lambda: [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.compose",
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/calendar.events.readonly",
        "https://www.googleapis.com/auth/calendar.events",
    ])
    user_email: str = "demo.partner@advisoryfirm.in"


@dataclass
class ZohoOAuthState:
    connected: bool = False
    server_url: str = "https://mcp.zoho.com"
    auth_type: str = "Authorization on Demand"
    client_id: str = ""
    client_secret: str = ""
    redirect_uri: str = "http://localhost:8501"
    access_token: str = ""
    refresh_token: str = ""
    expires_at: Optional[str] = None
    domain: str = "zoho.in"
    org_id: str = "org_802910"
    scopes: list = field(default_factory=lambda: [
        "ZohoCRM.modules.ALL",
        "ZohoBooks.fullaccess.ALL",
        "Desk.tickets.ALL",
        "Desk.basic.READ",
    ])
    user_email: str = "demo.partner@advisoryfirm.in"


class ClientVault:
    def __init__(self, execution_mode: str = "live"):
        self.execution_mode = execution_mode
        self.google = GoogleOAuthState()
        self.zoho = ZohoOAuthState()

        # Load environment variables
        self.google.client_id = os.getenv("GOOGLE_CLIENT_ID", "")
        self.google.client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
        self.google.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8501")
        self.google.access_token = os.getenv("GOOGLE_ACCESS_TOKEN", "")
        self.google.refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN", "")
        self.google.connected = bool(self.google.access_token)

        self.zoho.client_id = os.getenv("ZOHO_CLIENT_ID", "")
        self.zoho.client_secret = os.getenv("ZOHO_CLIENT_SECRET", "")
        self.zoho.redirect_uri = os.getenv("ZOHO_REDIRECT_URI", "http://localhost:8501")
        self.zoho.access_token = os.getenv("ZOHO_ACCESS_TOKEN", "")
        self.zoho.refresh_token = os.getenv("ZOHO_REFRESH_TOKEN", "")
        self.zoho.domain = os.getenv("ZOHO_DOMAIN", "zoho.in")
        self.zoho.connected = bool(self.zoho.access_token)

    def get_google_auth_url(self) -> str:
        """
        Builds Google authorization URL for OAuth 2.0.
        """
        if not self.google.client_id:
            return ""
        return OAuthManager.get_google_auth_url(
            client_id=self.google.client_id,
            redirect_uri=self.google.redirect_uri,
            scopes=self.google.scopes,
        )

    def handle_google_code_exchange(self, code: str, state: Optional[str] = None) -> Dict[str, Any]:
        """
        Exchanges Google auth code for tokens via OAuth 2.0.
        """
        result = OAuthManager.exchange_google_code(
            client_id=self.google.client_id,
            client_secret=self.google.client_secret,
            code=code,
            redirect_uri=self.google.redirect_uri,
        )

        if "access_token" in result:
            self.google.access_token = result["access_token"]
            if "refresh_token" in result:
                self.google.refresh_token = result["refresh_token"]
            expires_in = result.get("expires_in", 3600)
            self.google.expires_at = (datetime.datetime.now() + datetime.timedelta(seconds=expires_in)).strftime("%Y-%m-%d %H:%M:%S")
            self.google.connected = True
        return result

    def get_google_access_token(self) -> str:
        """
        Returns a valid Google access token, auto-refreshing via refresh_token if expired.
        """
        if self.google.expires_at:
            exp = datetime.datetime.strptime(self.google.expires_at, "%Y-%m-%d %H:%M:%S")
            if datetime.datetime.now() > exp:
                if self.google.refresh_token and self.google.client_id and self.google.client_secret:
                    ref_res = OAuthManager.refresh_google_token(
                        client_id=self.google.client_id,
                        client_secret=self.google.client_secret,
                        refresh_token=self.google.refresh_token,
                    )
                    if "access_token" in ref_res:
                        self.google.access_token = ref_res["access_token"]
                        expires_in = ref_res.get("expires_in", 3600)
                        self.google.expires_at = (datetime.datetime.now() + datetime.timedelta(seconds=expires_in)).strftime("%Y-%m-%d %H:%M:%S")
                        return self.google.access_token
                self.google.access_token = ""
                self.google.expires_at = None
                return ""
        return self.google.access_token

    def disconnect_google(self) -> bool:
        """
        Revokes the token at Google Accounts and clears local memory.
        """
        if self.google.access_token:
            OAuthManager.revoke_google_token(self.google.access_token)
        self.google.access_token = ""
        self.google.refresh_token = ""
        self.google.expires_at = None
        self.google.connected = False
        return True

    def get_zoho_auth_url(self) -> str:
        """
        Builds Zoho authorization URL for OAuth 2.0.
        """
        if not self.zoho.client_id:
            return ""
        return OAuthManager.get_zoho_auth_url(
            client_id=self.zoho.client_id,
            domain=self.zoho.domain,
            redirect_uri=self.zoho.redirect_uri,
            scopes=self.zoho.scopes,
        )

    def handle_zoho_code_exchange(self, code: str, state: Optional[str] = None) -> Dict[str, Any]:
        """
        Exchanges Zoho auth code for tokens via OAuth 2.0.
        """
        result = OAuthManager.exchange_zoho_code(
            client_id=self.zoho.client_id,
            client_secret=self.zoho.client_secret,
            domain=self.zoho.domain,
            code=code,
            redirect_uri=self.zoho.redirect_uri,
        )

        if "access_token" in result:
            self.zoho.access_token = result["access_token"]
            if "refresh_token" in result:
                self.zoho.refresh_token = result["refresh_token"]
            expires_in = result.get("expires_in", 3600)
            self.zoho.expires_at = (datetime.datetime.now() + datetime.timedelta(seconds=expires_in)).strftime("%Y-%m-%d %H:%M:%S")
            self.zoho.connected = True
        return result

    def get_zoho_access_token(self) -> str:
        """
        Returns a valid Zoho access token, auto-refreshing via refresh_token if expired.
        """
        if self.zoho.expires_at:
            exp = datetime.datetime.strptime(self.zoho.expires_at, "%Y-%m-%d %H:%M:%S")
            if datetime.datetime.now() > exp:
                if self.zoho.refresh_token and self.zoho.client_id and self.zoho.client_secret:
                    ref_res = OAuthManager.refresh_zoho_token(
                        client_id=self.zoho.client_id,
                        client_secret=self.zoho.client_secret,
                        domain=self.zoho.domain,
                        refresh_token=self.zoho.refresh_token,
                    )
                    if "access_token" in ref_res:
                        self.zoho.access_token = ref_res["access_token"]
                        expires_in = ref_res.get("expires_in", 3600)
                        self.zoho.expires_at = (datetime.datetime.now() + datetime.timedelta(seconds=expires_in)).strftime("%Y-%m-%d %H:%M:%S")
                        return self.zoho.access_token
                self.zoho.access_token = ""
                self.zoho.expires_at = None
                return ""
        return self.zoho.access_token

    def disconnect_zoho(self) -> bool:
        """
        Revokes the token at Zoho Accounts and clears local memory.
        """
        if self.zoho.access_token:
            OAuthManager.revoke_zoho_token(self.zoho.domain, self.zoho.access_token)
        self.zoho.access_token = ""
        self.zoho.refresh_token = ""
        self.zoho.expires_at = None
        self.zoho.connected = False
        return True

    def is_google_authenticated(self) -> bool:
        return bool(self.get_google_access_token())

    def is_zoho_authenticated(self) -> bool:
        return bool(self.get_zoho_access_token())

    def update_google_credentials(
        self, client_id: str, client_secret: str, redirect_uri: str = "http://localhost:8501", access_token: str = "", refresh_token: str = ""
    ):
        self.google.client_id = client_id
        self.google.client_secret = client_secret
        self.google.redirect_uri = redirect_uri
        if access_token:
            self.google.access_token = access_token
        if refresh_token:
            self.google.refresh_token = refresh_token
        self.google.connected = bool(self.google.access_token)

    def update_zoho_credentials(
        self,
        client_id: str,
        client_secret: str,
        domain: str = "zoho.in",
        redirect_uri: str = "http://localhost:8501",
        access_token: str = "",
        refresh_token: str = "",
    ):
        self.zoho.client_id = client_id
        self.zoho.client_secret = client_secret
        self.zoho.domain = domain
        self.zoho.redirect_uri = redirect_uri
        if access_token:
            self.zoho.access_token = access_token
        if refresh_token:
            self.zoho.refresh_token = refresh_token
        self.zoho.connected = bool(self.zoho.access_token)

    def get_status(self) -> Dict[str, Any]:
        return {
            "mode": self.execution_mode,
            "google": {
                "connected": self.is_google_authenticated(),
                "client_id": self.google.client_id,
                "has_secret": bool(self.google.client_secret),
                "is_live": self.is_google_authenticated(),
                "expires_at": self.google.expires_at,
                "email": self.google.user_email,
                "scopes": self.google.scopes,
            },
            "zoho": {
                "connected": self.is_zoho_authenticated(),
                "domain": self.zoho.domain,
                "client_id": self.zoho.client_id,
                "has_secret": bool(self.zoho.client_secret),
                "is_live": self.is_zoho_authenticated(),
                "expires_at": self.zoho.expires_at,
                "email": self.zoho.user_email,
                "scopes": self.zoho.scopes,
            },
        }

