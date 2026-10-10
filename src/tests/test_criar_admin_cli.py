# src/tests/test_criar_admin_cli.py
"""
Testes para o script de criação do administrador inicial
(app/cli/criar_admin.py).

Estratégia:
- `AsyncSessionLocal` é substituído por uma fábrica de teste que devolve
  a sessão de teste (`db_session`, fixture do conftest.py), para que o
  script opere sobre o mesmo banco de testes/transação.
- `input()` e `getpass.getpass()` são simulados via monkeypatch.
"""
import contextlib

import pytest
from sqlalchemy import select

from app.cli import criar_admin as criar_admin_module
from app.models.usuario import PerfilUsuario, Usuario

pytestmark = pytest.mark.asyncio


def _fabrica_sessao_de_teste(db_session):
    """Substitui AsyncSessionLocal: ao ser chamada (AsyncSessionLocal()),
    deve devolver um context manager que entrega a sessão de teste."""

    @contextlib.asynccontextmanager
    async def _context_manager():
        yield db_session

    def _factory():
        return _context_manager()

    return _factory


def _simular_entradas(monkeypatch, respostas_input, respostas_senha):
    """Simula input() e getpass.getpass() retornando valores em sequência."""
    iterador_input = iter(respostas_input)
    iterador_senha = iter(respostas_senha)

    monkeypatch.setattr("builtins.input", lambda *_: next(iterador_input))
    monkeypatch.setattr(
        criar_admin_module.getpass, "getpass", lambda *_: next(iterador_senha)
    )


class TestCriarAdminSucesso:
    async def test_cria_administrador_com_dados_validos(self, db_session, monkeypatch):
        monkeypatch.setattr(
            criar_admin_module,
            "AsyncSessionLocal",
            _fabrica_sessao_de_teste(db_session),
        )
        _simular_entradas(
            monkeypatch,
            respostas_input=["Admin Teste", "admin@paroquia.com"],
            respostas_senha=["senha_valida123", "senha_valida123"],
        )

        await criar_admin_module.criar_admin()

        resultado = await db_session.execute(
            select(Usuario).where(Usuario.email == "admin@paroquia.com")
        )
        admin = resultado.scalar_one_or_none()

        assert admin is not None
        assert admin.nome == "Admin Teste"
        assert admin.perfil == PerfilUsuario.ADMINISTRADOR
        assert admin.ativo is True
        assert admin.senha_hash != "senha_valida123"  # garante que foi hasheada


class TestCriarAdminValidacoes:
    async def test_nao_cria_quando_ja_existe_administrador(
        self, db_session, monkeypatch
    ):
        existente = Usuario(
            nome="Admin Existente",
            email="existente@paroquia.com",
            senha_hash="hash_qualquer",
            perfil=PerfilUsuario.ADMINISTRADOR,
            ativo=True,
        )
        db_session.add(existente)
        await db_session.commit()

        monkeypatch.setattr(
            criar_admin_module,
            "AsyncSessionLocal",
            _fabrica_sessao_de_teste(db_session),
        )
        _simular_entradas(
            monkeypatch,
            respostas_input=["Novo Admin", "novo@paroquia.com"],
            respostas_senha=["senha_valida123", "senha_valida123"],
        )

        await criar_admin_module.criar_admin()

        resultado = await db_session.execute(
            select(Usuario).where(Usuario.email == "novo@paroquia.com")
        )
        assert resultado.scalar_one_or_none() is None

    async def test_nao_cria_quando_senhas_nao_coincidem(self, db_session, monkeypatch):
        monkeypatch.setattr(
            criar_admin_module,
            "AsyncSessionLocal",
            _fabrica_sessao_de_teste(db_session),
        )
        _simular_entradas(
            monkeypatch,
            respostas_input=["Admin Teste", "admin2@paroquia.com"],
            respostas_senha=["senha_valida123", "senha_diferente"],
        )

        await criar_admin_module.criar_admin()

        resultado = await db_session.execute(
            select(Usuario).where(Usuario.email == "admin2@paroquia.com")
        )
        assert resultado.scalar_one_or_none() is None

    async def test_nao_cria_quando_senha_e_curta(self, db_session, monkeypatch):
        monkeypatch.setattr(
            criar_admin_module,
            "AsyncSessionLocal",
            _fabrica_sessao_de_teste(db_session),
        )
        _simular_entradas(
            monkeypatch,
            respostas_input=["Admin Teste", "admin3@paroquia.com"],
            respostas_senha=["123", "123"],
        )

        await criar_admin_module.criar_admin()

        resultado = await db_session.execute(
            select(Usuario).where(Usuario.email == "admin3@paroquia.com")
        )
        assert resultado.scalar_one_or_none() is None
