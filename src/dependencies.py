"""
Dependencies and configuration management for the API server.
"""
from functools import lru_cache
from fastapi import Depends
from typing import Optional
from pydantic import BaseSettings

from config import ServerConfig, AuthConfig, AuthType, BasicAuthConfig
from auth.auth_manager import AuthManager

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    servicenow_instance_url: str = "https://your-instance.service-now.com"
    servicenow_username: Optional[str] = None
    servicenow_password: Optional[str] = None
    servicenow_oauth_token: Optional[str] = None
    servicenow_api_key: Optional[str] = None
    auth_type: str = "basic"  # basic, oauth, or apikey
    request_timeout: int = 30

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()

def get_config(settings: Settings = Depends(get_settings)) -> ServerConfig:
    """Get ServiceNow server configuration."""
    auth_config = None
    
    if settings.auth_type == "basic" and settings.servicenow_username and settings.servicenow_password:
        auth_config = AuthConfig(
            type=AuthType.BASIC,
            basic=BasicAuthConfig(
                username=settings.servicenow_username,
                password=settings.servicenow_password
            )
        )
    # TODO: Add other auth type configurations
    
    return ServerConfig(
        instance_url=settings.servicenow_instance_url,
        auth=auth_config,
        timeout=settings.request_timeout
    )

def get_auth_manager(config: ServerConfig = Depends(get_config)) -> AuthManager:
    """Get authentication manager instance."""
    return AuthManager(config=config)