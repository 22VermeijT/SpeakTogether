"""
Configuration settings for SpeakTogether backend
Environment-based configuration with validation
"""

import os
from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Application Configuration
    APP_NAME: str = "SpeakTogether"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Server Configuration
    HOST: str = "localhost"
    PORT: int = 8000
    RELOAD: bool = True
    
    # Google Cloud Configuration
    GOOGLE_APPLICATION_CREDENTIALS: str = ""
    GOOGLE_CLOUD_PROJECT: str = ""
    
    # Google ADK Configuration
    ADK_API_KEY: str = ""
    ADK_PROJECT_ID: str = ""
    
    # WebSocket Configuration
    WS_MAX_CONNECTIONS: int = 100
    WS_PING_INTERVAL: int = 30
    
    # Audio Processing Configuration
    AUDIO_SAMPLE_RATE: int = 16000
    AUDIO_CHUNK_SIZE: int = 1024
    AUDIO_CHANNELS: int = 1
    
    # Translation Configuration
    DEFAULT_SOURCE_LANGUAGE: str = "auto"
    DEFAULT_TARGET_LANGUAGE: str = "en"
    MAX_TRANSLATION_LENGTH: int = 5000
    
    # Agent Configuration
    AGENT_TIMEOUT: int = 30
    AGENT_MAX_RETRIES: int = 3
    AGENT_CONFIDENCE_THRESHOLD: float = 0.7
    
    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE: str = "logs/speaktogether.log"
    
    # Security Configuration
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # Performance Configuration
    MAX_CONCURRENT_SESSIONS: int = 50
    CACHE_TTL: int = 300
    RATE_LIMIT_PER_MINUTE: int = 100
    
    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v
    
    @field_validator('GOOGLE_APPLICATION_CREDENTIALS')
    @classmethod
    def validate_google_credentials(cls, v):
        if v and not os.path.exists(v):
            raise ValueError(f"Google credentials file not found: {v}")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings() 