import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from typing import List

load_dotenv()

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # API Keys
    ANTHROPIC_API_KEY: str
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_DATABASE_PASSWORD: str  # ✅ Campo agregado para evitar error
    PINECONE_API_KEY: str
    PINECONE_ENVIRONMENT: str

    # Application Settings
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    EMBEDDING_MODEL: str = "claude-3-haiku-20240307"
    VECTOR_DIMENSION: int = 1536

    # Default Categories
    DEFAULT_INCOME_CATEGORIES: List[str] = [
        "Revenue", "Investment", "Grant", "Interest", "Other Income"
    ]
    DEFAULT_EXPENSE_CATEGORIES: List[str] = [
        "Payroll", "Software", "Marketing", "Office", "Services", 
        "Hardware", "Travel", "Legal", "Taxes", "Other Expense"
    ]

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "forbid"  # Evita que se filtren variables no declaradas

# Create settings instance
settings = Settings()

# For testing
if __name__ == "__main__":
    print(f"Environment: {settings.APP_ENV}")
    print(f"Log Level: {settings.LOG_LEVEL}")
    print(f"Embedding Model: {settings.EMBEDDING_MODEL}")
