import os
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_ID: str = "workkbot"
    REGION: str = "asia-south1"
    ENVIRONMENT: str = "development"
    PORT: int = 8080

    # Database Configuration
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 5432
    DB_NAME: str = "workkbot"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = ""
    DB_USE_IAM_AUTH: bool = False
    DB_SSL_MODE: str = "prefer"  # 'require', 'verify-ca', 'prefer', 'disable'

    # Auth & GCIP
    GCIP_ISSUER_URL: str = "https://securetoken.google.com/workkbot"
    TEST_MODE: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("REGION")
    @classmethod
    def validate_sovereign_region(cls, v: str) -> str:
        if v != "asia-south1":
            raise ValueError(
                f"Sovereignty violation: Region '{v}' is prohibited. Must be strictly 'asia-south1' (Mumbai)."
            )
        return v


settings = Settings()
