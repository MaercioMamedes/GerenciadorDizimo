import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decodificar_access_token
from app.db.session import get_db  # ajuste conforme o caminho real do módulo
from app.models.usuario import PerfilUsuario, Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Usuario:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decodificar_access_token(token)
    if payload is None:
        raise credentials_exception

    usuario_id = payload.get("sub")
    if usuario_id is None:
        raise credentials_exception

    try:
        usuario_uuid = uuid.UUID(usuario_id)
    except ValueError as e:
        raise credentials_exception from e

    resultado = await db.execute(select(Usuario).where(Usuario.id == usuario_uuid))
    usuario = resultado.scalar_one_or_none()

    if usuario is None or not usuario.ativo:
        raise credentials_exception

    return usuario


def require_perfil(*perfis_permitidos: PerfilUsuario):
    """Factory de dependência para restringir endpoints por perfil (RBAC)."""

    def verificador(usuario: Usuario = Depends(get_current_user)) -> Usuario:
        if usuario.perfil not in perfis_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para acessar este recurso.",
            )
        return usuario

    return verificador


async def get_db_com_auditoria(
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AsyncSession:
    """
    Retorna a sessão do banco já com o usuario_id propagado via SET LOCAL,
    necessário para os triggers de auditoria (audit_log).
    """
    await db.execute(
        text("SET LOCAL app.usuario_id = :usuario_id"),
        {"usuario_id": str(usuario.id)},
    )
    return db


# Atalhos prontos para uso nos routers
require_admin = require_perfil(PerfilUsuario.ADMINISTRADOR)
require_dizimista = require_perfil(PerfilUsuario.DIZIMISTA)
