from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from urllib.parse import quote_plus

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    API_V1_STR: str = ""
    BACKEND_CORS_ORIGINS: list[str] = []

    @computed_field
    def CORS_ORIGINS(self) -> list[str]:
        return self.BACKEND_CORS_ORIGINS
    
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "testdb"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str
    POSTGRES_POOL_SIZE: int = 5
    POSTGRES_MAX_OVERFLOW: int = 10
    POSTGRES_TIMEZONE: str = "UTC"

    LOGTO_INTROSPECTION_ENDPOINT: str = (
        "https://example.com/oidc/token/introspection"
    )
    LOGTO_CLIENT_ID: str = ""
    LOGTO_CLIENT_SECRET: str = ""

    VITE_LOGTO_ENDPOINT: str = ""
    VITE_LOGTO_APP_ID: str = ""

    @computed_field
    @property
    def sqlalchemy_database_uri(self) -> str:
        password = quote_plus(self.POSTGRES_PASSWORD)
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{password}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
config = Settings()
