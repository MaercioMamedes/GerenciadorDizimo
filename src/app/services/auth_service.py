from datetime import datetime, timedelta, timezone
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.security import verificar_senha, criar_access_token
from app.models.usuario import Usuario
from app.models.security_log import SecurityLog


async def _registrar_log(
    db: AsyncSession,
    evento: str,
    usuario_id: uuid.UUID | None = None,
    ip_origem: str | None = None,
    detalhes: str | None = None,
) -> None:
    """Persiste um evento de segurança."""
    log = SecurityLog(
        usuario_id=usuario_id,
        evento=evento,
        ip_origem=ip_origem,
        detalhes=detalhes,
    )
    db.add(log)
    await db.commit()


async def autenticar_usuario(
    db: AsyncSession, email: str, senha: str, ip_origem: str | None = None
) -> Usuario:
    """
    Valida credenciais, aplica política de bloqueio por tentativas falhas
    e retorna o usuário autenticado. Lança HTTPException em caso de falha.
    """
    resultado = await db.execute(select(Usuario).where(Usuario.email == email))
    usuario = resultado.scalar_one_or_none()

    # Usuário não existe: não revelar esse detalhe (evita enumeração de e-mails)
    if usuario is None:
        await _registrar_log(db, "login_falha", detalhes=f"email inexistente: {email}", ip_origem=ip_origem)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas.",
        )

    agora = datetime.now(timezone.utc)

    # Verifica se está bloqueado
    if usuario.bloqueado_até and usuario.bloqueado_até > agora:
        await _registrar_log(db, "login_bloqueado", usuario_id=usuario.id, ip_origem=ip_origem)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Conta bloqueada até {usuario.bloqueado_até.isoformat()}. Tente novamente mais tarde.",
        )

    # Conta inativa
    if not usuario.ativo:
        await _registrar_log(db, "login_falha", usuario_id=usuario.id, detalhes="conta inativa", ip_origem=ip_origem)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conta desativada. Contate o administrador.",
        )

    # Senha incorreta
    if not verificar_senha(senha, usuario.senha_hash):
        usuario.tentativas_falhas += 1

        if usuario.tentativas_falhas >= settings.max_tentativas_login:
            usuario.bloqueado_até = agora + timedelta(minutes=settings.tempo_bloqueio_minutos)
            await db.commit()
            await _registrar_log(db, "bloqueio", usuario_id=usuario.id, ip_origem=ip_origem)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Número máximo de tentativas excedido. Conta bloqueada por {settings.tempo_bloqueio_minutos} minutos.",
            )

        await db.commit()
        await _registrar_log(db, "login_falha", usuario_id=usuario.id, ip_origem=ip_origem)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas.",
        )

    # Sucesso: reseta contadores de bloqueio
    usuario.tentativas_falhas = 0
    usuario.bloqueado_até = None
    await db.commit()

    await _registrar_log(db, "login_sucesso", usuario_id=usuario.id, ip_origem=ip_origem)
    return usuario


def gerar_token_para_usuario(usuario: Usuario) -> str:
    return criar_access_token(usuario_id=str(usuario.id), perfil=usuario.perfil.value)
