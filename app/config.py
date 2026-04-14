from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    CRM_API_URL: str = "https://dashboard-api-production-e8b4.up.railway.app/api/meta-crm"
    CRM_API_KEY: str

    SUPABASE_URL: str
    SUPABASE_KEY: str

    DEFAULT_START_DATE: str = "2026-01-01"
    DEFAULT_END_DATE: str = "2026-03-26"

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash-lite"

    CHATBOT_API_KEY: str = ""
    ALLOWED_ORIGINS: str = "*"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
