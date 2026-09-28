import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.usuario import PerfilUsuario


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CadastroUsuarioRequest(BaseModel):
    nome: str
    email: EmailStr
    senha: str


class UsuarioAutenticado(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    email: EmailStr
    telefone: str | None
    data_nascimento: date | None
    perfil: PerfilUsuario
    paroquia_id: uuid.UUID | None
    ativo: bool
