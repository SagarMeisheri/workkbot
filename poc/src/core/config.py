"""
Workkbot Local PoC: Core Configuration
"""
from dataclasses import dataclass, field
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class AppConfig:
    execution_mode: str = os.getenv("WORKKBOT_EXECUTION_MODE", "live")  # "sandbox" or "live"
    gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY", "")
    
    # Google OAuth 2.0
    google_client_id: Optional[str] = os.getenv("GOOGLE_CLIENT_ID", "")
    google_client_secret: Optional[str] = os.getenv("GOOGLE_CLIENT_SECRET", "")
    google_redirect_uri: str = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8501")
    google_access_token: Optional[str] = os.getenv("GOOGLE_ACCESS_TOKEN", "")
    google_refresh_token: Optional[str] = os.getenv("GOOGLE_REFRESH_TOKEN", "")
    
    # Zoho OAuth 2.0
    zoho_client_id: Optional[str] = os.getenv("ZOHO_CLIENT_ID", "")
    zoho_client_secret: Optional[str] = os.getenv("ZOHO_CLIENT_SECRET", "")
    zoho_redirect_uri: str = os.getenv("ZOHO_REDIRECT_URI", "http://localhost:8501")
    zoho_access_token: Optional[str] = os.getenv("ZOHO_ACCESS_TOKEN", "")
    zoho_refresh_token: Optional[str] = os.getenv("ZOHO_REFRESH_TOKEN", "")
    zoho_domain: str = os.getenv("ZOHO_DOMAIN", "zoho.in")
    
    # Persistence & Webhooks
    session_db_url: str = os.getenv("SESSION_DB_URL", "sqlite+aiosqlite:///poc_sessions.db")
    webhook_host: str = os.getenv("WEBHOOK_HOST", "127.0.0.1")
    webhook_port: int = int(os.getenv("WEBHOOK_PORT", "8000"))

    # Guardrails
    enable_pii_masking: bool = os.getenv("ENABLE_PRESIDIO_PII_MASKING", "true").lower() == "true"
    enable_injection_shield: bool = os.getenv("ENABLE_INJECTION_SHIELD", "true").lower() == "true"
    require_hitl_for_writes: bool = os.getenv("REQUIRE_HITL_FOR_WRITES", "true").lower() == "true"


def get_config() -> AppConfig:
    return AppConfig()
