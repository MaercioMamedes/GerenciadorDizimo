"""Testes genéricos para modelos que usam TimestampMixin."""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy import text

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


async def test_timestamps_possuem_timezone_utc(db_session, admin_factory):
    """Garante que criado_em e atualizado_em são salvos com timezone UTC explícito."""
    usuario = await admin_factory(db_session)

    assert usuario.criado_em is not None
    assert usuario.atualizado_em is not None

    assert usuario.criado_em.tzinfo is not None
    assert usuario.atualizado_em.tzinfo is not None

    agora_utc = datetime.now(UTC)
    assert abs(usuario.criado_em - agora_utc) < timedelta(seconds=5)
    assert abs(usuario.atualizado_em - agora_utc) < timedelta(seconds=5)


async def test_atualizado_em_e_atualizado_na_edicao(db_session, admin_factory):
    """Garante que atualizado_em muda após uma atualização no banco."""
    usuario = await admin_factory(db_session)

    criado_em_original = usuario.criado_em
    atualizado_em_original = usuario.atualizado_em

    import asyncio

    await asyncio.sleep(0.05)

    usuario.nome = "Nome Atualizado Timestamp"
    await db_session.commit()
    await db_session.refresh(usuario)

    assert usuario.criado_em == criado_em_original
    assert usuario.atualizado_em > atualizado_em_original


async def test_timestamp_nao_e_naive(db_session, admin_factory):
    """Garante que o ORM não persiste datetime naive na coluna de timestamp."""
    usuario = await admin_factory(db_session)

    result = await db_session.execute(
        text("SELECT criado_em, atualizado_em FROM usuario WHERE id = :id"),
        {"id": str(usuario.id)},
    )
    row = result.one()

    for value in (row.criado_em, row.atualizado_em):
        assert isinstance(value.tzinfo, timezone)
        assert value.utcoffset().total_seconds() == 0


async def test_template_filter_converte_para_fuso_local():
    """Garante que o filtro Jinja2 converte UTC para America/Maceio."""
    from app.core.template_filters import format_dt

    utc = datetime(2026, 10, 20, 8, 0, 0, tzinfo=UTC)
    formatado = format_dt(utc, "%d/%m/%Y %H:%M")

    assert formatado == "20/10/2026 05:00"


async def test_template_filter_retorna_traco_para_valor_nulo():
    """Garante que o filtro trata valores nulos de forma segura."""
    from app.core.template_filters import format_dt

    assert format_dt(None) == "—"


