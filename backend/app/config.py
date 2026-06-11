"""Application configuration settings."""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Ollama Configuration
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    
    # Server Configuration
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False
    log_level: str = "INFO"
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./gd_platform.db"
    
    # Input Limits
    max_message_length: int = 2000
    
    # Session Settings
    session_duration_minutes: int = 10  # Default, can be overridden per session
    preparation_time_seconds: int = 60  # Thinking time before discussion starts (exactly 30s)
    max_context_messages: int = 15
    bot_response_timeout: int = 45
    
    # Turn-taking Settings
    min_turn_delay: float = 2.0
    max_turn_delay: float = 3.0
    user_priority_turns: int = 4  # Increased to reduce spam
    user_silence_threshold: int = 30  # 30 seconds before inviting user
    max_user_invitations: int = 2  # Maximum reminders per session
    
    # CORS Settings
    cors_origins: list = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
