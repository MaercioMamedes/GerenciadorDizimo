from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str
    postgres_port: int
    database_url: str

    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    app_env: str = "development"
    app_debug: bool = True

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
