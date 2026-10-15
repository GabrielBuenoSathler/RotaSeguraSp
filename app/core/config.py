from datetime import date

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    postgres_user: str
    postgres_password: str
    postgres_host: str
    postgres_port: int
    app_env: str = "development"
    postgres_database: str = "Criminalidade"
    sql_echo: bool = False
    database_statement_timeout_ms: int = Field(default=15000, ge=100, le=120000)
    valhalla_url: str = "http://valhalla:8002"
    valhalla_timeout_seconds: float = Field(default=30, gt=0)
    route_alternates: int = Field(default=2, ge=0, le=2)
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    risk_radius_meters: int = Field(default=50, ge=1, le=1000)
    occurrence_date_column: str | None = Field(
        default=None, pattern=r"^[a-z_][a-z0-9_]*$"
    )
    occurrence_group_date_column: str | None = Field(
        default=None, pattern=r"^[a-z_][a-z0-9_]*$"
    )
    risk_window_days: int = Field(default=365, ge=1, le=3650)
    dataset_source: str = "Base de ocorrências importada pelo administrador"
    dataset_updated_at: date | None = None
    nominatim_url: str | None = None
    geocoder_user_agent: str = "RotaSeguraSP/0.1"

    @field_validator(
        "occurrence_date_column",
        "occurrence_group_date_column",
        "dataset_updated_at",
        "nominatim_url",
        mode="before",
    )
    @classmethod
    def empty_optional(cls, value):
        return None if value == "" else value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
