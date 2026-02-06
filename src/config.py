from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://hitl:hitl_dev_password@localhost/hitl_credit"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = "http://localhost:3000"


settings = Settings()
