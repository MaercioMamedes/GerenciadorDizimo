"""Testes de unidade para usuario_service e perfil_dizimista_service."""

from unittest.mock import MagicMock, patch

import pytest

from app.models.usuario import PerfilUsuario
from app.schemas.usuario import UsuarioCreate, UsuarioUpdate
from app.services.perfil_dizimista_service import (
    sugerir_numero_registro,
    validar_numero_registro_unico,
)
from app.services.usuario_service import atualizar_usuario, criar_usuario

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Fixtures helpers
# ---------------------------------------------------------------------------


def _mock_execute_scalar(mock_session, retorno):
    resultado_fake = MagicMock()
    resultado_fake.scalar_one_or_none.return_value = retorno
    mock_session.execute.return_value = resultado_fake
    return resultado_fake


# ---------------------------------------------------------------------------
# criar_usuario
# ---------------------------------------------------------------------------


async def test_criar_usuario_sucesso(mock_session):
    dados = UsuarioCreate(
        nome="Maercio Teste",
        email="maercio@teste.com",
        senha="senha12345",
        perfil=PerfilUsuario.DIZIMISTA,
    )

    _mock_execute_scalar(mock_session, None)

    with patch("app.services.usuario_service.hash_senha", return_value="hash_fake"):
        usuario = await criar_usuario(mock_session, dados)

    assert usuario.nome == "Maercio Teste"
    assert usuario.email == "maercio@teste.com"
    assert usuario.senha_hash == "hash_fake"
    mock_session.add.assert_called_once_with(usuario)
    mock_session.commit.assert_awaited_once()


async def test_criar_usuario_dizimista_sem_email_e_sem_senha(mock_session):
    """Admin pode cadastrar um dizimista sem e-mail e sem senha."""
    dados = UsuarioCreate(
        nome="Dizimista Sem Acesso",
        email=None,
        senha=None,
        perfil=PerfilUsuario.DIZIMISTA,
    )

    _mock_execute_scalar(mock_session, None)

    with patch("app.services.usuario_service.hash_senha", return_value="hash_fake"):
        usuario = await criar_usuario(mock_session, dados)

    assert usuario.email is None
    assert usuario.senha_hash == "hash_fake"
    mock_session.add.assert_called_once_with(usuario)
    mock_session.commit.assert_awaited_once()


async def test_criar_usuario_email_duplicado_lanca_erro(mock_session):
    dados = UsuarioCreate(
        nome="Duplicado",
        email="duplicado@teste.com",
        senha="senha12345",
        perfil=PerfilUsuario.DIZIMISTA,
    )

    usuario_existente = MagicMock()
    _mock_execute_scalar(mock_session, usuario_existente)

    with pytest.raises(Exception) as exc_info:
        await criar_usuario(mock_session, dados)

    assert exc_info.value.status_code == 409
    assert "e-mail" in exc_info.value.detail.lower()


async def test_criar_usuario_nao_verifica_email_quando_email_nulo(mock_session):
    """Quando e-mail é None, o service não deve executar a query de duplicidade."""
    dados = UsuarioCreate(
        nome="Sem Email",
        email=None,
        senha=None,
        perfil=PerfilUsuario.DIZIMISTA,
    )

    _mock_execute_scalar(mock_session, None)

    with patch("app.services.usuario_service.hash_senha", return_value="hash_fake"):
        await criar_usuario(mock_session, dados)

    # A query deveria ter sido executada 0 vezes porque não há e-mail para verificar.
    # Nota: hash_senha é chamado mesmo sem senha (gera UUID internamente).
    mock_session.execute.assert_not_awaited()


# ---------------------------------------------------------------------------
# atualizar_usuario
# ---------------------------------------------------------------------------


async def test_atualizar_usuario_altera_email(mock_session):
    usuario = MagicMock()
    usuario.email = "antigo@teste.com"

    _mock_execute_scalar(mock_session, None)

    dados = UsuarioUpdate(
        nome="Atualizado",
        email="novo@teste.com",
        perfil=PerfilUsuario.DIZIMISTA,
        ativo=True,
    )

    await atualizar_usuario(mock_session, usuario, dados)

    assert usuario.email == "novo@teste.com"
    assert usuario.nome == "Atualizado"
    mock_session.commit.assert_awaited_once()


async def test_atualizar_usuario_permite_remover_email(mock_session):
    """Deve permitir limpar o e-mail de um dizimista cadastrado pelo admin."""
    usuario = MagicMock()
    usuario.email = "antigo@teste.com"

    _mock_execute_scalar(mock_session, None)

    dados = UsuarioUpdate(
        nome="Atualizado",
        email=None,
        perfil=PerfilUsuario.DIZIMISTA,
        ativo=True,
    )

    await atualizar_usuario(mock_session, usuario, dados)

    assert usuario.email is None
    mock_session.commit.assert_awaited_once()


async def test_atualizar_usuario_nao_verifica_email_quando_email_nulo(mock_session):
    usuario = MagicMock()
    usuario.email = "antigo@teste.com"

    dados = UsuarioUpdate(
        nome="Atualizado",
        email=None,
        perfil=PerfilUsuario.DIZIMISTA,
        ativo=True,
    )

    await atualizar_usuario(mock_session, usuario, dados)

    mock_session.execute.assert_not_awaited()


# ---------------------------------------------------------------------------
# perfil_dizimista_service
# ---------------------------------------------------------------------------


async def test_sugerir_numero_registro_retorna_proximo_disponivel(mock_session):
    resultado_fake = MagicMock()
    resultado_fake.scalar_one_or_none.return_value = 42
    mock_session.execute.return_value = resultado_fake

    sugerido = await sugerir_numero_registro(mock_session)

    assert sugerido == 43


async def test_sugerir_numero_registro_retorna_1_quando_nenhum(mock_session):
    resultado_fake = MagicMock()
    resultado_fake.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = resultado_fake

    sugerido = await sugerir_numero_registro(mock_session)

    assert sugerido == 1


async def test_validar_numero_registro_unico_permite_nulo(mock_session):
    await validar_numero_registro_unico(mock_session, None)
    mock_session.execute.assert_not_awaited()


async def test_validar_numero_registro_unico_permite_quando_nao_existe(mock_session):
    _mock_execute_scalar(mock_session, None)

    await validar_numero_registro_unico(mock_session, 123)

    mock_session.execute.assert_awaited_once()


async def test_validar_numero_registro_unico_rejeita_duplicado(mock_session):
    perfil_existente = MagicMock()
    resultado_fake = MagicMock()
    resultado_fake.scalar_one_or_none.return_value = perfil_existente
    mock_session.execute.return_value = resultado_fake

    with pytest.raises(ValueError, match="já está em uso"):
        await validar_numero_registro_unico(mock_session, 123)
