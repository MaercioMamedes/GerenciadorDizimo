"""Testes unitários do mecanismo de busca e filtro de usuários.

Cobrem os filtros individuais e combinados do serviço
`listar_usuarios_paginado`, além da paginação e da resiliência a
valores inválidos.
"""

from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.perfil_dizimista import StatusCadastro
from app.models.usuario import PerfilUsuario, Usuario
from app.services.usuario_query_service import listar_usuarios_paginado

pytestmark = pytest.mark.asyncio


# --------------------------------------------------------------------------- #
# Testes de filtro individual
# --------------------------------------------------------------------------- #
async def test_listar_sem_filtros_retorna_todos(
    db_session: AsyncSession,
    usuarios_filtro: dict[str, Usuario],
):
    resultado = await listar_usuarios_paginado(db_session)

    assert resultado["total_registros"] == 5
    assert len(resultado["itens"]) == 5
    assert resultado["pagina"] == 1
    assert resultado["total_paginas"] == 1


async def test_filtro_por_nome(
    db_session: AsyncSession,
    usuarios_filtro: dict[str, Usuario],
):
    resultado = await listar_usuarios_paginado(db_session, busca="Carlos")

    assert resultado["total_registros"] == 1
    assert resultado["itens"][0].nome == "Carlos Dizimista"


async def test_filtro_por_nome_case_insensitive(
    db_session: AsyncSession,
    usuarios_filtro: dict[str, Usuario],
):
    resultado = await listar_usuarios_paginado(db_session, busca="JOÃO")

    assert resultado["total_registros"] == 1
    assert resultado["itens"][0].nome == "João Admin"


async def test_filtro_por_numero_registro(
    db_session: AsyncSession,
    usuarios_filtro: dict[str, Usuario],
):
    resultado = await listar_usuarios_paginado(db_session, numero_registro=1234)

    assert resultado["total_registros"] == 1
    assert resultado["itens"][0].nome == "Carlos Dizimista"


async def test_filtro_por_numero_registro_inexistente(
    db_session: AsyncSession,
    usuarios_filtro: dict[str, Usuario],
):
    resultado = await listar_usuarios_paginado(db_session, numero_registro=9999)

    assert resultado["total_registros"] == 0
    assert resultado["itens"] == []


async def test_filtro_por_data_nascimento(
    db_session: AsyncSession,
    usuarios_filtro: dict[str, Usuario],
):
    resultado = await listar_usuarios_paginado(db_session, data_nascimento=date(1990, 3, 22))

    assert resultado["total_registros"] == 1
    assert resultado["itens"][0].nome == "Ana Dizimista"


async def test_filtro_por_perfil_administrador(
    db_session: AsyncSession,
    usuarios_filtro: dict[str, Usuario],
):
    resultado = await listar_usuarios_paginado(db_session, perfil=PerfilUsuario.ADMINISTRADOR)

    assert resultado["total_registros"] == 2
    nomes = {u.nome for u in resultado["itens"]}
    assert nomes == {"João Admin", "Maria Admin Inativa"}


async def test_filtro_por_perfil_dizimista(
    db_session: AsyncSession,
    usuarios_filtro: dict[str, Usuario],
):
    resultado = await listar_usuarios_paginado(db_session, perfil=PerfilUsuario.DIZIMISTA)

    assert resultado["total_registros"] == 3


async def test_filtro_por_ativo_true(
    db_session  : AsyncSession,
    usuarios_filtro: dict[str, Usuario],
):
    resultado = await listar_usuarios_paginado(db_session, ativo=True)

    assert resultado["total_registros"] == 3
    assert all(u.ativo for u in resultado["itens"])


async def test_filtro_por_ativo_false(
    db_session: AsyncSession,
    usuarios_filtro: dict[str, Usuario],
):
    resultado = await listar_usuarios_paginado(db_session, ativo=False)

    assert resultado["total_registros"] == 2
    assert all(not u.ativo for u in resultado["itens"])


async def test_filtro_por_status_cadastro_pendente(
    db_session: AsyncSession,
    usuarios_filtro: dict[str, Usuario],
):
    resultado = await listar_usuarios_paginado(
        db_session, status_cadastro=StatusCadastro.PENDENTE
    )

    assert resultado["total_registros"] == 1
    assert resultado["itens"][0].nome == "Ana Dizimista"


async def test_filtro_por_status_cadastro_aprovado(
    db_session: AsyncSession,
    usuarios_filtro: dict[str, Usuario],
):
    resultado = await listar_usuarios_paginado(
        db_session, status_cadastro=StatusCadastro.APROVADO
    )

    assert resultado["total_registros"] == 1
    assert resultado["itens"][0].nome == "Carlos Dizimista"


async def test_filtro_por_status_cadastro_rejeitado(
    db_session: AsyncSession,
    usuarios_filtro: dict[str, Usuario],
):
    resultado = await listar_usuarios_paginado(
        db_session, status_cadastro=StatusCadastro.REJEITADO
    )

    assert resultado["total_registros"] == 1
    assert resultado["itens"][0].nome == "Bruno Rejeitado"


# --------------------------------------------------------------------------- #
# Testes de combinação de filtros
# --------------------------------------------------------------------------- #
async def test_combinacao_nome_e_perfil(
    db_session: AsyncSession,
    usuarios_filtro: dict[str, Usuario],
):
    resultado = await listar_usuarios_paginado(
        db_session,
        busca="Maria",
        perfil=PerfilUsuario.ADMINISTRADOR,
    )

    assert resultado["total_registros"] == 1
    assert resultado["itens"][0].nome == "Maria Admin Inativa"


async def test_combinacao_perfil_ativo_e_status(
    db_session: AsyncSession,
    usuarios_filtro: dict[str, Usuario],
):
    resultado = await listar_usuarios_paginado(
        db_session,
        perfil=PerfilUsuario.DIZIMISTA,
        ativo=True,
        status_cadastro=StatusCadastro.REJEITADO,
    )

    assert resultado["total_registros"] == 1
    assert resultado["itens"][0].nome == "Bruno Rejeitado"


async def test_combinacao_filtros_sem_resultado(
    db_session: AsyncSession,
    usuarios_filtro: dict[str, Usuario],
):
    resultado = await listar_usuarios_paginado(
        db_session,
        busca="Inexistente",
        perfil=PerfilUsuario.DIZIMISTA,
        ativo=True,
    )

    assert resultado["total_registros"] == 0


# --------------------------------------------------------------------------- #
# Testes de paginação
# --------------------------------------------------------------------------- #
async def test_paginacao_retorna_tamanho_correto(
    db_session: AsyncSession,
    usuarios_filtro: dict[str, Usuario],
):
    resultado = await listar_usuarios_paginado(db_session, pagina=1, tamanho_pagina=2)

    assert len(resultado["itens"]) == 2
    assert resultado["total_registros"] == 5
    assert resultado["total_paginas"] == 3


async def test_paginacao_segunda_pagina(
    db_session: AsyncSession,
    usuarios_filtro: dict[str, Usuario],
):
    resultado = await listar_usuarios_paginado(db_session, pagina=2, tamanho_pagina=2)

    assert len(resultado["itens"]) == 2
    assert resultado["pagina"] == 2


async def test_paginacao_ultima_pagina_parcial(
    db_session: AsyncSession,
    usuarios_filtro: dict[str, Usuario],
):
    resultado = await listar_usuarios_paginado(db_session, pagina=3, tamanho_pagina=2)

    assert len(resultado["itens"]) == 1
    assert resultado["pagina"] == 3


# --------------------------------------------------------------------------- #
# Testes de valores inválidos / vazios
# --------------------------------------------------------------------------- #
async def test_filtros_vazios_sao_ignorados(
    db_session: AsyncSession,
    usuarios_filtro: dict[str, Usuario],
):
    """Filtros None ou vazios não devem restringir o resultado."""
    resultado = await listar_usuarios_paginado(
        db_session,
        busca=None,
        numero_registro=None,
        data_nascimento=None,
        perfil=None,
        ativo=None,
        status_cadastro=None,
    )

    assert resultado["total_registros"] == 5


async def test_filtro_por_perfil_invalido_retorna_vazio(
    db_session: AsyncSession,
    usuarios_filtro: dict[str, Usuario],
):
    """Passar um perfil inválido (não existente no enum) retorna lista vazia."""
    resultado = await listar_usuarios_paginado(
        db_session,
        perfil="perfil_inexistente",  # type: ignore[arg-type]
    )

    assert resultado["total_registros"] == 0
