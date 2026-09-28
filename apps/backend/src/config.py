"""Application settings and environment configuration."""
import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Workkbot Backend"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))
    
    # Supabase credentials (loaded from .env in development, or Google Cloud Secret Manager in Cloud Run)
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""
    
    # Reviewer Sandbox (Apple Guideline 2.1)
    REVIEWER_EMAIL: str = "apple-reviewer@workkbot.in"
    REVIEWER_PASSWORD: str = os.getenv("REVIEWER_PASSWORD", "ReviewerDemo2026!Secured")
    REVIEWER_ORG_ID: str = "e0000000-0000-0000-0000-000000000002"
    
    # Agentgateway
    AGENTGATEWAY_URL: str = os.getenv("AGENTGATEWAY_URL", "http://127.0.0.1:8080")
    
    # Google Workspace OAuth
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    
    # Zoho Workplace OAuth
    ZOHO_CLIENT_ID: str = os.getenv("ZOHO_CLIENT_ID", "")
    ZOHO_CLIENT_SECRET: str = os.getenv("ZOHO_CLIENT_SECRET", "")
    ZOHO_ACCOUNTS_URL: str = "https://accounts.zoho.in"
    
    # DPDP
    CURRENT_CONSENT_VERSION: str = "2026.1"

    # LLM & Agentgateway Configuration (Spec 02)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    SUPABASE_DB_URL: str = os.getenv("SUPABASE_DB_URL", "")
    VERTEX_AI_PROJECT: str = os.getenv("VERTEX_AI_PROJECT", "workkbot-prod-asia-south1")
    VERTEX_AI_LOCATION: str = os.getenv("VERTEX_AI_LOCATION", "asia-south1")
    DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "gemini-3.8-flash")
    FALLBACK_MODEL: str = os.getenv("FALLBACK_MODEL", "gemini-3.7-flash")
    LLM_TIMEOUT_SECONDS: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "30"))
    
    model_config = {
        "env_file": [
            str(Path(__file__).resolve().parent.parent / ".env"),
            ".env",
        ],
        "extra": "allow",
    }


settings = Settings()

# Ensure Gemini API keys are accessible to google.adk and google.genai
if settings.GEMINI_API_KEY and not os.environ.get("GEMINI_API_KEY"):
    os.environ["GEMINI_API_KEY"] = settings.GEMINI_API_KEY
if settings.GOOGLE_API_KEY and not os.environ.get("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = settings.GOOGLE_API_KEY
