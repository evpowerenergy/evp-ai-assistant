"""
Application Configuration
"""
from pydantic_settings import BaseSettings, SettingsConfigDict  # type: ignore[reportMissingImports]
from typing import List
from pydantic import field_validator
import json
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # Supabase
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    
    # OpenAI
    OPENAI_API_KEY: str
    # เปลี่ยน model ได้ที่ไฟล์ .env โดยใส่ OPENAI_MODEL=ชื่อโมเดล (เช่น gpt-5.4, gpt-5.4-mini)
    # ค่า default ด้านล่างใช้เมื่อ .env ไม่ได้กำหนด OPENAI_MODEL
    OPENAI_MODEL: str = "gpt-5.4-mini"
    
    # LINE
    LINE_CHANNEL_SECRET: str = ""
    LINE_CHANNEL_ACCESS_TOKEN: str = ""
    
    # App
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    API_PORT: int = 8000
    
    # CORS - Accept string, will be parsed to list via property
    # Can be set as comma-separated string: "http://localhost:3000,http://localhost:3001"
    # Or as JSON array: '["http://localhost:3000","http://localhost:3001"]'
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001"
    
    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS from string or list to string"""
        # If None or empty, return default
        if v is None or v == "":
            return "http://localhost:3000,http://localhost:3001"
        
        # If already a string, return as is (strip whitespace)
        if isinstance(v, str):
            return v.strip()
        
        # If list, convert to comma-separated string
        if isinstance(v, list):
            # Filter out empty items and join with comma
            items = [str(item).strip() for item in v if item]
            return ','.join(items) if items else "http://localhost:3000"
        
        # Convert any other type to string
        return str(v).strip() if v else "http://localhost:3000,http://localhost:3001"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS_ORIGINS as a list"""
        if not self.CORS_ORIGINS:
            return ["http://localhost:3000", "http://localhost:3001"]
        
        # Parse comma-separated string
        if ',' in self.CORS_ORIGINS:
            origins = [origin.strip() for origin in self.CORS_ORIGINS.split(',') if origin.strip()]
            return origins if origins else ["http://localhost:3000"]
        
        # Try to parse as JSON array
        v_stripped = self.CORS_ORIGINS.strip()
        if v_stripped.startswith('[') and v_stripped.endswith(']'):
            try:
                parsed = json.loads(v_stripped)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if item]
            except (json.JSONDecodeError, ValueError):
                pass
        
        # Single string
        return [v_stripped] if v_stripped else ["http://localhost:3000"]
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
