from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "AI Onboarding Backend"
    APP_ENV: str = "development"
    CORS_ORIGINS: str = ""

    DATABASE_URL: str

    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536

    @property
    def cors_origins_list(self) -> list[str]:
        return [
            origin.strip().rstrip("/")
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]

    class Config:
        env_file = ".env"


settings = Settings()
