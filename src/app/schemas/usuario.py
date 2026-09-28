import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.usuario import PerfilUsuario


class UsuarioCreate(BaseModel):
    nome: str = Field(min_length=3, max_length=150)
    email: EmailStr
    senha: str = Field(min_length=8, max_length=100)
    telefone: str | None = Field(default=None, max_length=20)
    data_nascimento: date | None = None
    perfil: PerfilUsuario
    paroquia_id: uuid.UUID | None = None

    @field_validator("paroquia_id")
    @classmethod
    def validar_paroquia_para_admin(cls, v, info):
        perfil = info.data.get("perfil")
        if perfil == PerfilUsuario.ADMINISTRADOR and v is None:
            raise ValueError("paroquia_id é obrigatório para o perfil ADMINISTRADOR.")
        return v


class UsuarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    email: EmailStr
    telefone: str | None
    data_nascimento: date | None
    perfil: PerfilUsuario
    paroquia_id: uuid.UUID | None
    ativo: bool
