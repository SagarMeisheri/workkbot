"""
Workkbot Local PoC: Dual OAuth 2.0 Engine for Google Workspace & Zoho Suite
Implements RFC 6749 Authorization Code Flow with offline refresh tokens,
region-specific Zoho accounts endpoints, and async token exchange.
"""
from typing import Any, Dict, List, Optional
import urllib.parse
import httpx


class OAuthManager:
    """
    Standardized OAuth 2.0 authentication manager for Google and Zoho.
    Implements RFC 6749 Authorization Code Flow with offline access and token refresh.
    """

    # Google Workspace Standard Endpoints
    GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"

    DEFAULT_GOOGLE_SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.compose",
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/calendar.events.readonly",
        "https://www.googleapis.com/auth/calendar.events",
    ]

    DEFAULT_ZOHO_SCOPES = [
        "ZohoCRM.modules.ALL",
        "ZohoBooks.fullaccess.ALL",
        "Desk.tickets.ALL",
        "Desk.basic.READ",
    ]

    @staticmethod
    def get_google_auth_url(
        client_id: str,
        redirect_uri: str = "http://localhost:8501",
        scopes: Optional[List[str]] = None,
        state: str = "provider=google",
    ) -> str:
        """
        Builds Google OAuth 2.0 authorization code URL with offline access.
        """
        if not scopes:
            scopes = OAuthManager.DEFAULT_GOOGLE_SCOPES

        params: Dict[str, str] = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "access_type": "online",
            "state": state,
        }
        return f"{OAuthManager.GOOGLE_AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}"

    @staticmethod
    def exchange_google_code(
        client_id: str,
        client_secret: str,
        code: str,
        redirect_uri: str = "http://localhost:8501",
    ) -> Dict[str, Any]:
        """
        Exchanges Google authorization code for access and refresh tokens using OAuth 2.0.
        """
        data: Dict[str, str] = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(OAuthManager.GOOGLE_TOKEN_ENDPOINT, data=data)
                return resp.json()
        except Exception as e:
            return {"error": str(e), "error_description": "Failed to connect to Google OAuth token endpoint."}

    @staticmethod
    def refresh_google_token(
        client_id: str,
        client_secret: str,
        refresh_token: str,
    ) -> Dict[str, Any]:
        """
        Uses refresh_token to acquire a new Google access_token.
        """
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(OAuthManager.GOOGLE_TOKEN_ENDPOINT, data=data)
                return resp.json()
        except Exception as e:
            return {"error": str(e), "error_description": "Failed to refresh Google access token."}

    @staticmethod
    def get_zoho_accounts_url(domain: str = "zoho.in") -> str:
        """
        Resolves domain-specific Zoho Accounts endpoint (e.g. accounts.zoho.in).
        """
        clean_domain = domain.strip().lower().replace("accounts.", "").replace("https://", "")
        return f"https://accounts.{clean_domain}"

    @staticmethod
    def get_zoho_auth_url(
        client_id: str,
        domain: str = "zoho.in",
        redirect_uri: str = "http://localhost:8501",
        scopes: Optional[List[str]] = None,
        state: str = "provider=zoho",
    ) -> str:
        """
        Builds domain-specific Zoho OAuth 2.0 authorization URL with offline access.
        """
        if not scopes:
            scopes = OAuthManager.DEFAULT_ZOHO_SCOPES

        base_url = OAuthManager.get_zoho_accounts_url(domain)
        params: Dict[str, str] = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": ",".join(scopes),
            "access_type": "online",
            "state": state,
        }
        return f"{base_url}/oauth/v2/auth?{urllib.parse.urlencode(params)}"

    @staticmethod
    def exchange_zoho_code(
        client_id: str,
        client_secret: str,
        domain: str,
        code: str,
        redirect_uri: str = "http://localhost:8501",
    ) -> Dict[str, Any]:
        """
        Exchanges Zoho authorization code for access and refresh tokens via OAuth 2.0.
        """
        base_url = OAuthManager.get_zoho_accounts_url(domain)
        data: Dict[str, str] = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(f"{base_url}/oauth/v2/token", data=data)
                return resp.json()
        except Exception as e:
            return {"error": str(e), "error_description": "Failed to connect to Zoho OAuth token endpoint."}

    @staticmethod
    def revoke_google_token(token: str) -> bool:
        """
        Immediately revokes Google access token upstream.
        """
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    f"https://oauth2.googleapis.com/revoke?token={token}",
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                return resp.status_code == 200
        except Exception:
            return False

    @staticmethod
    def revoke_zoho_token(domain: str, token: str) -> bool:
        """
        Immediately revokes Zoho access token upstream.
        """
        try:
            base_url = OAuthManager.get_zoho_accounts_url(domain)
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    f"{base_url}/oauth/v2/token/revoke?token={token}",
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                return resp.status_code == 200
        except Exception:
            return False

    @staticmethod
    def refresh_zoho_token(
        client_id: str,
        client_secret: str,
        domain: str,
        refresh_token: str,
    ) -> Dict[str, Any]:
        """
        Uses refresh_token to acquire a fresh Zoho access_token.
        """
        base_url = OAuthManager.get_zoho_accounts_url(domain)
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(f"{base_url}/oauth/v2/token", data=data)
                return resp.json()
        except Exception as e:
            return {"error": str(e), "error_description": "Failed to refresh Zoho access token."}
