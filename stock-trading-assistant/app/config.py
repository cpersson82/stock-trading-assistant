"""
Configuration management for Stock Trading Assistant
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from functools import lru_cache
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Email Configuration
    email_sender: str = Field(default="", description="Gmail address for sending")
    email_password: str = Field(default="", description="Gmail App Password")
    email_recipient: str = Field(default="", description="Email to receive recommendations")
    resend_api_key: str = Field(default="", description="Resend API key")
    
    # AI Chat
    anthropic_api_key: str = Field(default="", description="Anthropic API key for AI chat")
    
    # API Keys
    alpha_vantage_api_key: str = Field(default="demo", description="Alpha Vantage API key")
    finnhub_api_key: Optional[str] = Field(default=None, description="Finnhub API key")
    
    # Application Settings
    secret_key: str = Field(default="dev-secret-key-change-in-production")
    database_url: str = Field(default="sqlite:///./data/trading.db")
    user_timezone: str = Field(default="Europe/Zurich")
    base_currency: str = Field(default="CHF")
    
    # Recommendation Settings
    max_daily_recommendations: int = Field(default=3)
    quiet_hours_start: int = Field(default=23)  # 23:00
    quiet_hours_end: int = Field(default=7)     # 07:00
    system_active: bool = Field(default=True)
    
    # Portfolio Settings
    moderate_allocation: float = Field(default=0.70)
    aggressive_allocation: float = Field(default=0.30)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Risk categories for stocks
RISK_CATEGORIES = {
    "conservative": {
        "description": "Low volatility, large-cap, dividend-paying stocks",
        "max_position_pct": 0.25,
        "stop_loss_pct": 0.08,
    },
    "moderate": {
        "description": "Mid-cap stocks with reasonable volatility",
        "max_position_pct": 0.15,
        "stop_loss_pct": 0.12,
    },
    "aggressive": {
        "description": "Small-cap, growth, or speculative stocks",
        "max_position_pct": 0.10,
        "stop_loss_pct": 0.18,
    },
}

# Market hours (in local exchange time)
MARKET_HOURS = {
    "US": {"open": "09:30", "close": "16:00", "timezone": "America/New_York"},
    "CA": {"open": "09:30", "close": "16:00", "timezone": "America/Toronto"},
    "EU": {"open": "09:00", "close": "17:30", "timezone": "Europe/London"},
    "CH": {"open": "09:00", "close": "17:30", "timezone": "Europe/Zurich"},
    "DE": {"open": "09:00", "close": "17:30", "timezone": "Europe/Berlin"},
}

# Exchanges mapping
EXCHANGE_INFO = {
    "NYSE": {"region": "US", "currency": "USD", "suffix": ""},
    "NASDAQ": {"region": "US", "currency": "USD", "suffix": ""},
    "TSX": {"region": "CA", "currency": "CAD", "suffix": ".TO"},
    "TSX-V": {"region": "CA", "currency": "CAD", "suffix": ".V"},
    "LSE": {"region": "EU", "currency": "GBP", "suffix": ".L"},
    "SIX": {"region": "CH", "currency": "CHF", "suffix": ".SW"},
    "XETRA": {"region": "DE", "currency": "EUR", "suffix": ".DE"},
}

# Analysis thresholds
ANALYSIS_THRESHOLDS = {
    "strong_buy": 75,
    "buy": 65,
    "hold_upper": 65,
    "hold_lower": 40,
    "sell": 40,
    "strong_sell": 25,
}
