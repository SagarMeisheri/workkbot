"""Application settings and environment configuration."""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Workkbot Backend"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))
    
    # Supabase credentials
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "http://127.0.0.1:54321")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "mock-anon-key-workkbot-local")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "mock-service-role-key-workkbot-local")
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "super-secret-jwt-token-with-at-least-32-bytes-long")
    
    # Reviewer Sandbox (Apple Guideline 2.1)
    REVIEWER_EMAIL: str = "apple-reviewer@workkbot.in"
    REVIEWER_PASSWORD: str = os.getenv("REVIEWER_PASSWORD", "ReviewerDemo2026!Secured")
    REVIEWER_ORG_ID: str = "e0000000-0000-0000-0000-000000000002"
    
    # Agentgateway
    AGENTGATEWAY_URL: str = os.getenv("AGENTGATEWAY_URL", "http://127.0.0.1:8080")
    
    # Google Workspace OAuth
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "mock-google-client-id")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "mock-google-client-secret")
    
    # Zoho Workplace OAuth
    ZOHO_CLIENT_ID: str = os.getenv("ZOHO_CLIENT_ID", "mock-zoho-client-id")
    ZOHO_CLIENT_SECRET: str = os.getenv("ZOHO_CLIENT_SECRET", "mock-zoho-client-secret")
    ZOHO_ACCOUNTS_URL: str = "https://accounts.zoho.in"
    
    # DPDP
    CURRENT_CONSENT_VERSION: str = "2026.1"
    
    model_config = {"env_file": ".env", "extra": "allow"}


settings = Settings()
