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
    POSTGRES_PASSWORD: str = ""
    POSTGRES_POOL_SIZE: int = 5
    POSTGRES_MAX_OVERFLOW: int = 10
    POSTGRES_TIMEZONE: str = "UTC"

    LOGTO_INTROSPECTION_ENDPOINT: str = (
        "https://example.com/oidc/token/introspection"
    )
    LOGTO_ENDPOINT: str = ""
    LOGTO_OIDC_TOKEN_ENDPOINT: str = ""
    LOGTO_CLIENT_ID: str = ""
    LOGTO_CLIENT_SECRET: str = ""
    LOGTO_JWKS_ENDPOINT: str = ""

    VITE_LOGTO_ENDPOINT: str = ""
    VITE_LOGTO_APP_ID: str = ""

    PAT_TOKEN_PREFIX: str = "lap"
    PAT_TOKEN_SIZE: int = 48

    GATEWAY_JWT_SECRET: str = "change-me"
    GATEWAY_JWT_EXPIRES_SECONDS: int = 3600
    GATEWAY_JWT_ISSUER: str = "remote-access-gateway"
    TARGET_SERVICE_BASE_URL: str = ""

    BASE_URL:str = "http://localhost:8000"
    @computed_field
    @property
    def sqlalchemy_database_uri(self) -> str:
        password = quote_plus(self.POSTGRES_PASSWORD)
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{password}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field
    @property
    def LOGTO_TOKEN_ENDPOINT(self) -> str:
        if self.LOGTO_OIDC_TOKEN_ENDPOINT:
            return self.LOGTO_OIDC_TOKEN_ENDPOINT
        if self.LOGTO_ENDPOINT:
            return self.LOGTO_ENDPOINT.rstrip("/") + "/oidc/token"
        return "https://example.com/oidc/token"
config = Settings()
