"""Application configuration using pydantic-settings."""
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Database
    db_host: str = Field("localhost", env="DB_HOST")
    db_port: int = Field(3306, env="DB_PORT")
    db_name: str = Field("mule_matrix", env="DB_NAME")
    db_user: str = Field("root", env="DB_USER")
    db_password: str = Field("", env="DB_PASSWORD")

    # App
    app_secret_key: str = Field("dev-secret-key", env="APP_SECRET_KEY")
    app_env: str = Field("development", env="APP_ENV")
    app_debug: bool = Field(True, env="APP_DEBUG")

    backend_host: str = Field("0.0.0.0", env="BACKEND_HOST")
    backend_port: int = Field(8000, env="BACKEND_PORT")

    # Monitoring
    monitoring_poll_interval_seconds: int = Field(2, env="MONITORING_POLL_INTERVAL_SECONDS")
    high_value_threshold: float = Field(1_000_000.0, env="HIGH_VALUE_THRESHOLD")

    # Synthetic Generator
    default_seed: int = Field(42, env="DEFAULT_SEED")
    default_num_accounts: int = Field(60, env="DEFAULT_NUM_ACCOUNTS")
    default_num_transactions: int = Field(500, env="DEFAULT_NUM_TRANSACTIONS")
    default_timespan_days: int = Field(30, env="DEFAULT_TIMESPAN_DAYS")

    @property
    def database_url(self) -> str:
        return (
            f"mysql+aiomysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
