# backend/fastapi_api/app/config.py
from pydantic import ConfigDict
from pydantic_settings import BaseSettings
from typing import List, Optional
 
class Settings(BaseSettings):
    app_name: str = "Teams Project Management API"
    app_version: str = "1.0.0"
    api_title: str = "Teams Project Management API"
    api_description: str = "A comprehensive API for managing team projects"
    debug: bool = True
 
    port: int = 8000
 
     # Microsoft Azure AD
    tenant_id: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    redirect_uri: Optional[str] = None
    microsoft_scope: Optional[str] = None
 
    cors_origins: str = "http://localhost:3000"  
    cors_credentials: bool = True
    cors_methods: List[str] = ["*"]
    cors_headers: List[str] = ["*"]
 
    secret_key: str
    database_url: Optional[str] = None
 
    model_config = ConfigDict(
        extra='ignore',    
        env_file='.env'
    )
 
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse comma-separated CORS origins into a list"""
        return [origin.strip() for origin in self.cors_origins.split(",")]
 
settings = Settings()
 