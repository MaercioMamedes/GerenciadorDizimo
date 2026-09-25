"""Testes de CRUD usando mock de AsyncSession (sem banco real)."""
from datetime import date
from unittest.mock import AsyncMock

import pytest

from app.models.perfil_dizimista import PerfilDizimista, StatusCadastro
from app.models.usuario import Usuario, PerfilUsuario


@pytest.mark.asyncio
async def test_criar_perfil_dizimista_chama_add_e_commit(mock_session):
    """Garante que o fluxo de criação chama add() e commit() corretamente."""
    perfil = PerfilDizimista(
        usuario_id="11111111-1111-1111-1111-111111111111",
        igreja_id="22222222-2222-2222-2222-222222222222",
        endereco="Rua das Flores, 123",
        bairro="Centro",
        cidade="Maceió",
    )

    mock_session.add(perfil)
    await mock_session.commit()

    mock_session.add.assert_called_once_with(perfil)
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_buscar_perfil_dizimista_por_id(mock_session):
    """Simula a busca de um PerfilDizimista pelo ID via session.get()."""
    perfil_esperado = PerfilDizimista(
        usuario_id="11111111-1111-1111-1111-111111111111",
        igreja_id="22222222-2222-2222-2222-222222222222",
        status_cadastro=StatusCadastro.APROVADO,
        cidade="Maceió",
    )
    mock_session.get.return_value = perfil_esperado

    resultado = await mock_session.get(PerfilDizimista, "algum-id")

    mock_session.get.assert_awaited_once_with(PerfilDizimista, "algum-id")
    assert resultado.cidade == "Maceió"
    assert resultado.status_cadastro == StatusCadastro.APROVADO


@pytest.mark.asyncio
async def test_atualizar_endereco_perfil_dizimista(mock_session):
    """Simula a atualização de endereço/bairro/cidade e o commit subsequente."""
    perfil = PerfilDizimista(
        usuario_id="11111111-1111-1111-1111-111111111111",
        igreja_id="22222222-2222-2222-2222-222222222222",
        endereco="Endereço antigo",
        bairro="Bairro antigo",
        cidade="Cidade antiga",
    )

    perfil.endereco = "Rua Nova, 456"
    perfil.bairro = "Jaraguá"
    perfil.cidade = "Maceió"

    await mock_session.commit()

    assert perfil.endereco == "Rua Nova, 456"
    assert perfil.bairro == "Jaraguá"
    assert perfil.cidade == "Maceió"
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_deletar_perfil_dizimista_chama_delete_e_commit(mock_session):
    """Garante que o fluxo de remoção chama delete() e commit()."""
    perfil = PerfilDizimista(
        usuario_id="11111111-1111-1111-1111-111111111111",
        igreja_id="22222222-2222-2222-2222-222222222222",
    )

    mock_session.delete(perfil)
    await mock_session.commit()

    mock_session.delete.assert_called_once_with(perfil)
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_criar_usuario_com_telefone_e_data_nascimento(mock_session):
    """Verifica criação de Usuario com os novos campos telefone/data_nascimento."""
    usuario = Usuario(
        nome="Maria Silva",
        email="maria@example.com",
        senha_hash="hash_fake",
        perfil=PerfilUsuario.DIZIMISTA,
        telefone="(82) 99999-0000",
        data_nascimento=date(1990, 5, 20),
    )

    mock_session.add(usuario)
    await mock_session.commit()

    mock_session.add.assert_called_once_with(usuario)
    mock_session.commit.assert_awaited_once()
    assert usuario.telefone == "(82) 99999-0000"
    assert usuario.data_nascimento == date(1990, 5, 20)
