from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    upstream_base_url: str = "https://api.openai.com"
    default_model: str = "gpt-4.1-mini"
    fallback_model: str = "gpt-4.1"
    cheap_model: str = "gpt-4.1-nano"
    max_recent_messages: int = 8
    max_output_tokens: int = 1200
    cache_ttl_seconds: int = 86400
    database_path: str = "./data/token_shield.db"


settings = Settings()

