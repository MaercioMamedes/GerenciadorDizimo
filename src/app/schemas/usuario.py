import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.usuario import PerfilUsuario


class UsuarioCreate(BaseModel):
    """Usado no autocadastro público (UC03). Perfil é sempre dizimista
    e a definição de administrador/paróquia só ocorre na validação (UC04)."""

    nome: str = Field(min_length=3, max_length=150)
    email: EmailStr
    senha: str = Field(min_length=8, max_length=100)
    telefone: str | None = Field(default=None, max_length=20)
    data_nascimento: date | None = None
    perfil: PerfilUsuario = PerfilUsuario.DIZIMISTA
    paroquia_id: uuid.UUID | None = None


class UsuarioUpdate(BaseModel):
    """Usado pelo administrador para editar/validar um usuário existente
    (UC04/UC05). Permite definir perfil e paróquia."""

    nome: str = Field(min_length=3, max_length=150)
    email: EmailStr
    telefone: str | None = Field(default=None, max_length=20)
    data_nascimento: date | None = None
    perfil: PerfilUsuario
    paroquia_id: uuid.UUID | None = None
    ativo: bool = True

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
