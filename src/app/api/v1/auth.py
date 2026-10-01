from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.usuario import Usuario
from app.schemas.auth import LoginRequest, TokenResponse, UsuarioAutenticado
from app.services.auth_service import (
    autenticar_usuario,
    gerar_token_para_usuario,
    registrar_logout,
)

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/login", response_model=TokenResponse)
async def login(
    dados: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)
):
    ip_origem = request.client.host if request.client else None
    usuario = await autenticar_usuario(
        db, email=dados.email, senha=dados.senha, ip_origem=ip_origem
    )
    token = gerar_token_para_usuario(usuario)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UsuarioAutenticado)
async def me(usuario: Usuario = Depends(get_current_user)):
    return usuario

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ip_origem = request.client.host if request.client else None
    await registrar_logout(db, usuario=usuario, ip_origem=ip_origem)
