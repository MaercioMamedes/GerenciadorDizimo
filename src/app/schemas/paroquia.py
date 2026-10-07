import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ParoquiaBase(BaseModel):
    nome: str = Field(..., min_length=1, max_length=150)
    cnpj: str | None = Field(default=None, max_length=18)
    endereco: str | None = Field(default=None, max_length=255)


class ParoquiaCreate(ParoquiaBase):
    pass


class ParoquiaUpdate(ParoquiaBase):
    pass


class ParoquiaRead(ParoquiaBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
