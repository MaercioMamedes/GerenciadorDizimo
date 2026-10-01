import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.models.usuario import PerfilUsuario, Usuario
from app.services.auth_service import (
    autenticar_usuario,
    gerar_token_para_usuario,
    registrar_logout,
)


def _mock_scalar_result(mock_session, usuario):
    resultado = MagicMock()
    resultado.scalar_one_or_none.return_value = usuario
    mock_session.execute.return_value = resultado


def _criar_usuario_fake(**overrides) -> Usuario:

    dados = {
        "id": uuid.uuid4(),
        "nome": "Fulano",
        "email": "fulano@teste.com",
        "senha_hash": "hash_fake",
        "perfil": PerfilUsuario.DIZIMISTA,
        "ativo": True,
        "tentativas_falhas": 0,
        "bloqueado_até": None,
    }
    dados.update(overrides)
    return Usuario(**dados)


@pytest.mark.asyncio
async def test_autenticar_usuario_email_inexistente(mock_session):
    _mock_scalar_result(mock_session, None)

    with pytest.raises(HTTPException) as exc:
        await autenticar_usuario(
            mock_session, email="naoexiste@teste.com", senha="123456"
        )

    assert exc.value.status_code == 401
    assert exc.value.detail == "Credenciais inválidas."


@pytest.mark.asyncio
async def test_autenticar_usuario_conta_bloqueada(mock_session):
    futuro = datetime.now(UTC) + timedelta(minutes=10)
    usuario = _criar_usuario_fake(bloqueado_até=futuro)
    _mock_scalar_result(mock_session, usuario)

    with pytest.raises(HTTPException) as exc:
        await autenticar_usuario(mock_session, email=usuario.email, senha="123456")

    assert exc.value.status_code == 403
    assert "bloqueada" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_autenticar_usuario_conta_inativa(mock_session, monkeypatch):
    usuario = _criar_usuario_fake(ativo=False)
    _mock_scalar_result(mock_session, usuario)

    with pytest.raises(HTTPException) as exc:
        await autenticar_usuario(mock_session, email=usuario.email, senha="123456")

    assert exc.value.status_code == 403
    assert "desativada" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_autenticar_usuario_senha_incorreta(mock_session, monkeypatch):
    usuario = _criar_usuario_fake(tentativas_falhas=0)
    _mock_scalar_result(mock_session, usuario)

    monkeypatch.setattr(
        "app.services.auth_service.verificar_senha", lambda senha, hash_: False
    )

    with pytest.raises(HTTPException) as exc:
        await autenticar_usuario(mock_session, email=usuario.email, senha="errada")

    assert exc.value.status_code == 401
    assert usuario.tentativas_falhas == 1
    mock_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_autenticar_usuario_bloqueia_apos_max_tentativas(
    mock_session, monkeypatch
):
    usuario = _criar_usuario_fake(tentativas_falhas=settings.max_tentativas_login - 1)
    _mock_scalar_result(mock_session, usuario)

    monkeypatch.setattr(
        "app.services.auth_service.verificar_senha", lambda senha, hash_: False
    )

    with pytest.raises(HTTPException) as exc:
        await autenticar_usuario(mock_session, email=usuario.email, senha="errada")

    assert exc.value.status_code == 403
    assert "bloqueada" in exc.value.detail.lower()
    assert usuario.bloqueado_até is not None
    assert usuario.bloqueado_até > datetime.now(UTC)


@pytest.mark.asyncio
async def test_autenticar_usuario_sucesso(mock_session, monkeypatch):
    usuario = _criar_usuario_fake(tentativas_falhas=3)
    _mock_scalar_result(mock_session, usuario)

    monkeypatch.setattr(
        "app.services.auth_service.verificar_senha", lambda senha, hash_: True
    )

    resultado = await autenticar_usuario(
        mock_session, email=usuario.email, senha="correta"
    )

    assert resultado is usuario
    assert usuario.tentativas_falhas == 0
    assert usuario.bloqueado_até is None
    mock_session.commit.assert_awaited()


def test_gerar_token_para_usuario():
    usuario = _criar_usuario_fake(perfil=PerfilUsuario.ADMINISTRADOR)
    token = gerar_token_para_usuario(usuario)

    assert isinstance(token, str)
    assert len(token) > 0

@pytest.mark.asyncio
async def test_registrar_logout(mock_session):
    usuario = _criar_usuario_fake()

    await registrar_logout(mock_session, usuario=usuario, ip_origem="127.0.0.1")

    mock_session.add.assert_called_once()
    log_salvo = mock_session.add.call_args[0][0]

    assert log_salvo.evento == "logout"
    assert log_salvo.usuario_id == usuario.id
    assert log_salvo.ip_origem == "127.0.0.1"
    mock_session.commit.assert_awaited()
