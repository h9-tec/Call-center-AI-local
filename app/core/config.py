"""
Configuration management for Call Center AI
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from functools import lru_cache
import yaml

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application
    app_name: str = "Call Center AI"
    app_version: str = "1.0.0"
    environment: str = Field("development", env="ENVIRONMENT")
    debug: bool = Field(False, env="DEBUG")
    
    # Server
    host: str = Field("0.0.0.0", env="HOST")
    port: int = Field(8000, env="PORT")
    public_url: str = Field("http://localhost:8000", env="PUBLIC_URL")
    
    # Security
    secret_key: str = Field(..., env="SECRET_KEY")
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24
    
    # Telephony
    telephony_provider: str = Field("twilio", env="TELEPHONY_PROVIDER")
    twilio_account_sid: Optional[str] = Field(None, env="TWILIO_ACCOUNT_SID")
    twilio_auth_token: Optional[str] = Field(None, env="TWILIO_AUTH_TOKEN")
    twilio_phone_number: Optional[str] = Field(None, env="TWILIO_PHONE_NUMBER")
    twilio_webhook_url: Optional[str] = Field(None, env="TWILIO_WEBHOOK_URL")
    
    # Models
    whisper_model: str = Field("openai/whisper-tiny", env="WHISPER_MODEL")
    whisper_device: str = Field("cpu", env="WHISPER_DEVICE")
    ollama_host: str = Field("http://localhost:11434", env="OLLAMA_HOST")
    ollama_model: str = Field("llama3.2:3b", env="OLLAMA_MODEL")
    tts_model: str = Field("kokoro", env="TTS_MODEL")
    tts_voice: str = Field("af_heart", env="TTS_VOICE")
    
    # Agent settings
    agent_name: str = Field("AI Assistant", env="AGENT_NAME")
    
    # Database
    postgres_host: str = Field("localhost", env="POSTGRES_HOST")
    postgres_port: int = Field(5432, env="POSTGRES_PORT")
    postgres_db: str = Field("callcenter", env="POSTGRES_DB")
    postgres_user: str = Field("callcenter_user", env="POSTGRES_USER")
    postgres_password: str = Field(..., env="POSTGRES_PASSWORD")
    
    # Redis
    redis_host: str = Field("localhost", env="REDIS_HOST")
    redis_port: int = Field(6379, env="REDIS_PORT")
    redis_password: Optional[str] = Field(None, env="REDIS_PASSWORD")
    redis_db: int = Field(0, env="REDIS_DB")
    
    # Audio Processing
    vad_sensitivity: int = Field(3, env="VAD_SENSITIVITY")
    min_speech_duration_ms: int = Field(250, env="MIN_SPEECH_DURATION_MS")
    max_speech_duration_ms: int = Field(30000, env="MAX_SPEECH_DURATION_MS")
    silence_duration_ms: int = Field(1500, env="SILENCE_DURATION_MS")
    
    # Performance
    max_concurrent_calls: int = Field(100, env="MAX_CONCURRENT_CALLS")
    response_timeout_ms: int = Field(5000, env="RESPONSE_TIMEOUT_MS")
    
    # Monitoring
    enable_metrics: bool = Field(True, env="ENABLE_METRICS")
    enable_tracing: bool = Field(True, env="ENABLE_TRACING")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    
    # CORS
    allowed_origins: list[str] = Field(default_factory=lambda: ["*"])
    allowed_hosts: list[str] = Field(default_factory=lambda: ["*"])
    
    # Paths
    models_path: Path = Field(PROJECT_ROOT / "models", env="MODELS_PATH")
    logs_path: Path = Field(PROJECT_ROOT / "logs", env="LOGS_PATH")
    cache_path: Path = Field(PROJECT_ROOT / "cache", env="CACHE_PATH")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",  # Allow extra fields in .env file
    }
        
    @field_validator("models_path", "logs_path", "cache_path", mode='before')
    def create_directories(cls, v: Path) -> Path:
        """Ensure directories exist"""
        if isinstance(v, str):
            v = Path(v)
        v.mkdir(parents=True, exist_ok=True)
        return v
    
    @property
    def database_url(self) -> str:
        """PostgreSQL connection URL"""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
    
    @property
    def redis_url(self) -> str:
        """Redis connection URL"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    def load_config_file(self, config_file: Optional[str] = None) -> Dict[str, Any]:
        """Load additional configuration from YAML file"""
        if config_file is None:
            config_file = f"config-{self.environment}.yaml"
        
        config_path = PROJECT_ROOT / "config" / config_file
        if config_path.exists():
            with open(config_path, "r") as f:
                return yaml.safe_load(f)
        return {}


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Create settings instance
settings = get_settings()
