"""
Testes para o CLI de cadastro de Paróquia + Igreja Matriz
(app/cli/criar_paroquia.py).

Estratégia:
- Substitui `AsyncSessionLocal` por um context manager fake que devolve a
  fixture `db_session` do próprio projeto, para que o teste use o banco
  de testes já configurado (mesma abordagem de test_criar_admin_cli.py).
- Simula as respostas do usuário via monkeypatch em `builtins.input`,
  consumindo uma lista de respostas na ordem em que os prompts aparecem.
"""

import pytest
from sqlalchemy import select

from app.cli.criar_paroquia import criar_paroquia
from app.models.igreja import Igreja
from app.models.paroquia import Paroquia

pytestmark = pytest.mark.asyncio


class _SessionContextManagerFake:
    """Fake de AsyncSessionLocal() que apenas devolve a sessão de teste,
    sem abrir/fechar uma conexão nova (quem gerencia o ciclo é a fixture)."""

    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _preparar_inputs(monkeypatch, respostas: list[str]):
    """Substitui input() para consumir `respostas` em sequência."""
    iterador = iter(respostas)

    def fake_input(_prompt=""):
        return next(iterador)

    monkeypatch.setattr("builtins.input", fake_input)


def _preparar_sessao(monkeypatch, db_session):
    monkeypatch.setattr(
        "app.cli.criar_paroquia.AsyncSessionLocal",
        lambda: _SessionContextManagerFake(db_session),
    )


class TestCriarParoquiaComDadosValidos:
    async def test_cria_paroquia_e_igreja_matriz_com_cnpj(
        self, db_session, monkeypatch
    ):
        _preparar_sessao(monkeypatch, db_session)
        _preparar_inputs(
            monkeypatch,
            [
                "Paróquia São Francisco",  # nome_matriz
                "Rua das Flores, 100",  # endereco_matriz
                "12.345.678/0001-90",  # cnpj
            ],
        )

        await criar_paroquia()

        resultado = await db_session.execute(
            select(Paroquia).where(Paroquia.cnpj == "12.345.678/0001-90")
        )
        paroquia = resultado.scalar_one_or_none()
        assert paroquia is not None

        resultado = await db_session.execute(
            select(Igreja).where(Igreja.paroquia_id == paroquia.id)
        )
        matriz = resultado.scalar_one_or_none()
        assert matriz is not None
        assert matriz.is_matriz is True
        assert matriz.nome == "Paróquia São Francisco"
        assert matriz.endereco == "Rua das Flores, 100"

    async def test_cria_paroquia_sem_cnpj_quando_omitido(self, db_session, monkeypatch):
        _preparar_sessao(monkeypatch, db_session)
        _preparar_inputs(
            monkeypatch,
            [
                "Paróquia Sem CNPJ",
                "Avenida Central, 500",
                "",  # ENTER para pular o CNPJ
            ],
        )

        await criar_paroquia()

        resultado = await db_session.execute(
            select(Igreja).where(Igreja.nome == "Paróquia Sem CNPJ")
        )
        matriz = resultado.scalar_one_or_none()
        assert matriz is not None

        resultado = await db_session.execute(
            select(Paroquia).where(Paroquia.id == matriz.paroquia_id)
        )
        paroquia = resultado.scalar_one_or_none()
        assert paroquia is not None
        assert paroquia.cnpj is None


class TestValidacaoDeCamposObrigatorios:
    async def test_insiste_quando_nome_da_matriz_esta_vazio(
        self, db_session, monkeypatch
    ):
        _preparar_sessao(monkeypatch, db_session)
        _preparar_inputs(
            monkeypatch,
            [
                "",  # tentativa inválida (vazio)
                "Paróquia Reinsistida",  # tentativa válida
                "Rua Nova, 10",
                "",  # cnpj opcional
            ],
        )

        await criar_paroquia()

        resultado = await db_session.execute(
            select(Igreja).where(Igreja.nome == "Paróquia Reinsistida")
        )
        assert resultado.scalar_one_or_none() is not None

    async def test_insiste_quando_endereco_da_matriz_esta_vazio(
        self, db_session, monkeypatch
    ):
        _preparar_sessao(monkeypatch, db_session)
        _preparar_inputs(
            monkeypatch,
            [
                "Paróquia Endereco Reinsistido",
                "",  # tentativa inválida (vazio)
                "Rua Reinsistida, 20",  # tentativa válida
                "",  # cnpj opcional
            ],
        )

        await criar_paroquia()

        resultado = await db_session.execute(
            select(Igreja).where(Igreja.nome == "Paróquia Endereco Reinsistido")
        )
        matriz = resultado.scalar_one_or_none()
        assert matriz is not None
        assert matriz.endereco == "Rua Reinsistida, 20"


class TestCnpjDuplicado:
    async def test_nao_cria_paroquia_com_cnpj_ja_existente(
        self, db_session, monkeypatch
    ):
        cnpj_existente = "11.111.111/0001-11"

        paroquia_existente = Paroquia(cnpj=cnpj_existente)
        db_session.add(paroquia_existente)
        await db_session.flush()
        db_session.add(
            Igreja(
                nome="Matriz Já Existente",
                endereco="Rua Original, 1",
                is_matriz=True,
                paroquia_id=paroquia_existente.id,
            )
        )
        await db_session.commit()

        _preparar_sessao(monkeypatch, db_session)
        _preparar_inputs(
            monkeypatch,
            [
                "Tentativa Duplicada",
                "Rua Duplicada, 2",
                cnpj_existente,
            ],
        )

        await criar_paroquia()

        resultado = await db_session.execute(
            select(Igreja).where(Igreja.nome == "Tentativa Duplicada")
        )
        assert resultado.scalar_one_or_none() is None

        resultado = await db_session.execute(
            select(Paroquia).where(Paroquia.cnpj == cnpj_existente)
        )
        paroquias = resultado.scalars().all()
        assert len(paroquias) == 1
