import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ParoquiaCreate(BaseModel):
    """Usado apenas no CLI/service de criação: cria Paróquia + Igreja Matriz juntas."""

    cnpj: str | None = Field(default=None, max_length=18)
    nome_matriz: str = Field(..., min_length=1, max_length=150)
    endereco_matriz: str = Field(..., min_length=1, max_length=255)


class ParoquiaUpdate(BaseModel):
    cnpj: str | None = Field(default=None, max_length=18)


class ParoquiaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cnpj: str | None
    nome: str | None  # calculado via property, origem = igreja matriz
    endereco: str | None  # calculado via property, origem = igreja matriz
    criado_em: datetime
    atualizado_em: datetime
