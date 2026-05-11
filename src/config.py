"""Configuration management for BeVigil App Enrichment."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


class Config:
    """Application configuration."""

    # BeVigil API
    BEVIGIL_API_KEY: str = os.getenv("BEVIGIL_API_KEY", "")
    BEVIGIL_BASE_URL: str = "https://osint.bevigil.com"

    # Supabase (project URL + new secret API key sb_secret_..., not legacy service_role JWT)
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SECRET_KEY: str = os.getenv("SUPABASE_SECRET_KEY", "")

    # Processing Configuration
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "10"))
    REQUEST_DELAY: float = float(os.getenv("REQUEST_DELAY", "1.5"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))

    @classmethod
    def validate(cls) -> list[str]:
        """Validate required configuration. Returns list of missing keys."""
        missing = []
        if not cls.BEVIGIL_API_KEY:
            missing.append("BEVIGIL_API_KEY")
        if not cls.SUPABASE_URL:
            missing.append("SUPABASE_URL")
        if not cls.SUPABASE_SECRET_KEY:
            missing.append("SUPABASE_SECRET_KEY")
        return missing


# Singleton instance
config = Config()
