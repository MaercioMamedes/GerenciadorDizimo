"""
Dependências de autenticação para VIEWS (server-side rendering).

Diferente de app/api/v1/deps.py (que usa Bearer token/OAuth2PasswordBearer
para a futura API JSON), aqui o token é lido do cookie HTTPOnly setado
no login via formulário HTML.
"""
import uuid

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decodificar_access_token
from app.db.session import get_db
from app.models.usuario import PerfilUsuario, Usuario

NOME_COOKIE_TOKEN = "access_token"


async def get_usuario_atual_opcional(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Usuario | None:
    """
    Retorna o usuário logado via cookie, ou None se não houver sessão válida.
    Usado para páginas públicas (ex.: home) que precisam saber se há
    usuário logado, sem forçar erro quando não há.
    """
    token = request.cookies.get(NOME_COOKIE_TOKEN)
    if not token:
        return None

    payload = decodificar_access_token(token)
    if payload is None:
        return None

    usuario_id = payload.get("sub")
    if usuario_id is None:
        return None

    try:
        usuario_uuid = uuid.UUID(usuario_id)
    except ValueError:
        return None

    resultado = await db.execute(select(Usuario).where(Usuario.id == usuario_uuid))
    usuario = resultado.scalar_one_or_none()

    if usuario is None or not usuario.ativo:
        return None

    return usuario


class RedirecionarParaLogin(HTTPException):
    """Exceção especial que redireciona para a tela de login (em vez de 401 puro)."""

    def __init__(self, proxima_url: str | None = None):
        location = "/auth/login"
        if proxima_url:
            location = f"/auth/login?next={proxima_url}"
        super().__init__(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": location},
        )


async def exigir_usuario_logado(
    request: Request,
    usuario: Usuario | None = Depends(get_usuario_atual_opcional),
) -> Usuario:
    """Garante que há usuário logado; caso contrário, redireciona para /auth/login."""
    if usuario is None:
        raise RedirecionarParaLogin(proxima_url=str(request.url.path))
    return usuario


def exigir_perfil_view(*perfis_permitidos: PerfilUsuario):
    """Factory de dependência para RBAC em views 
    (equivalente ao require_perfil da API)."""

    def verificador(usuario: Usuario = Depends(exigir_usuario_logado)) -> Usuario:
        if usuario.perfil not in perfis_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para acessar este recurso.",
            )
        return usuario

    return verificador


# Atalhos prontos para uso nas views
require_admin_view = exigir_perfil_view(PerfilUsuario.ADMINISTRADOR)
require_dizimista_view = exigir_perfil_view(PerfilUsuario.DIZIMISTA)
