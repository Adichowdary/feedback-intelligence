from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Hindsight Configuration
    HINDSIGHT_BANK_ID: str = "feedback-intelligence"
    HINDSIGHT_LLM_PROVIDER: str = "openai"
    HINDSIGHT_LLM_MODEL: str = "gpt-4o-mini"
    HINDSIGHT_LLM_API_KEY: Optional[str] = None
    
    # OpenAI Configuration (for hindsight-litellm wrapper)
    OPENAI_API_KEY: Optional[str] = None
    
    # App Configuration
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = True

    # Set to true to boot the embedded Hindsight server (needs a real OpenAI key)
    HINDSIGHT_EMBEDDED: bool = False
    # Optional: connect to a remote Hindsight instance (e.g. Hindsight Cloud URL)
    HINDSIGHT_URL: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()

# Bank configuration for feedback intelligence
BANK_CONFIG = {
    "bank_id": settings.HINDSIGHT_BANK_ID,
    "name": "Product Feedback Intelligence",
    "mission": (
        "You are a Product Feedback Intelligence Agent. "
        "Your job is to analyze user feedback over time, identify patterns, "
        "track sentiment changes, and surface actionable product insights. "
        "You remember every piece of feedback and use historical context to "
        "answer questions about evolving user problems."
    ),
    "directives": [
        "Always cite specific feedback (date, product area, source) when making claims",
        "Distinguish between current feedback and historical patterns",
        "Never hallucinate feedback — only use recalled memories",
        "Quantify with counts when possible (e.g., '38 mentions of PDF uploads')"
    ],
    "disposition": {
        "skepticism": 3,
        "literalism": 2,
        "empathy": 4
    }
}

# Product areas for categorization
PRODUCT_AREAS = [
    "pdf_upload",
    "login",
    "notifications",
    "mobile_app",
    "billing",
    "dashboard",
    "search",
    "export",
    "integrations",
    "performance",
    "other"
]

# Feedback sources
FEEDBACK_SOURCES = [
    "support_ticket",
    "in_app_feedback",
    "email",
    "user_interview",
    "social_media",
    "app_store_review",
    "sales_call",
    "other"
]