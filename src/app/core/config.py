from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str
    postgres_port: int
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    max_tentativas_login: int = 5
    tempo_bloqueio_minutos: int = 15

    app_env: str = "development"
    app_debug: bool = True
    testing: bool = False

    @computed_field
    @property
    def nome_banco_efetivo(self) -> str:
        if self.testing:
            return f"{self.postgres_db}_test"
        return self.postgres_db

    @computed_field
    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.nome_banco_efetivo}"
        )


settings = Settings()
