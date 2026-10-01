"""Testes de unidade para criar_usuario, usando mock_session (sem banco real)."""

from unittest.mock import MagicMock, patch

import pytest

from app.models.usuario import PerfilUsuario
from app.schemas.usuario import UsuarioCreate
from app.services.usuario_service import criar_usuario

pytestmark = pytest.mark.asyncio


async def test_criar_usuario_sucesso(mock_session):
    # 1. Monta os dados de entrada, como se viessem de um formulário
    dados = UsuarioCreate(
        nome="Maercio Teste",
        email="maercio@teste.com",
        senha="senha12345",
        perfil=PerfilUsuario.DIZIMISTA,
    )

    # 2. Simula a resposta do banco quando o service verifica
    #    "esse e-mail já existe?" -> resposta: None (não existe)
    resultado_fake = MagicMock()
    resultado_fake.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = resultado_fake

    # 3. Substitui a função hash_senha por uma versão fake,
    #    só para não depender do bcrypt real neste teste
    with patch("app.services.usuario_service.hash_senha", return_value="hash_fake"):
        usuario = await criar_usuario(mock_session, dados)

    # 4. Verifica se o usuário foi montado corretamente
    assert usuario.nome == "Maercio Teste"
    assert usuario.email == "maercio@teste.com"
    assert usuario.senha_hash == "hash_fake"

    # 5. Verifica se o service "tentou salvar" no banco
    mock_session.add.assert_called_once_with(usuario)
    mock_session.commit.assert_awaited_once()
