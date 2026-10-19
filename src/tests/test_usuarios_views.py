"""Testes de integracao para as views de usuario (cadastro/edicao)."""

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select

from app.models.perfil_dizimista import PerfilDizimista
from app.models.usuario import PerfilUsuario, Usuario
from app.services.auth_service import gerar_token_para_usuario

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


async def _login_admin(async_client: AsyncClient, db_session, admin_factory):
    """Helper que cria um administrador e retorna o objeto admin."""
    admin = await admin_factory(db_session)
    token = gerar_token_para_usuario(admin)
    async_client.cookies.set("access_token", token)
    return admin


async def test_admin_cria_dizimista_sem_email_sem_senha(
    async_client: AsyncClient, db_session, admin_factory, igreja_factory
):
    admin = await _login_admin(async_client, db_session, admin_factory)
    igreja = await igreja_factory(db_session, paroquia_id=admin.paroquia_id)

    response = await async_client.post(
        "/usuarios/novo",
        data={
            "nome": "Dizimista Sem Email",
            "perfil": "dizimista",
            "igreja_id": str(igreja.id),
            "ativo": "true",
        },
        follow_redirects=False,
    )

    assert response.status_code == status.HTTP_303_SEE_OTHER
    assert response.headers["location"] == "/usuarios"

    result = await db_session.execute(
        select(Usuario).where(Usuario.nome == "Dizimista Sem Email")
    )
    usuario = result.scalar_one()

    assert usuario.email is None
    assert usuario.perfil == PerfilUsuario.DIZIMISTA
    assert usuario.ativo is True


async def test_admin_cria_dizimista_com_numero_registro(
    async_client: AsyncClient, db_session, admin_factory, igreja_factory
):
    admin = await _login_admin(async_client, db_session, admin_factory)
    igreja = await igreja_factory(db_session, paroquia_id=admin.paroquia_id)

    response = await async_client.post(
        "/usuarios/novo",
        data={
            "nome": "Dizimista Com Registro",
            "perfil": "dizimista",
            "igreja_id": str(igreja.id),
            "numero_registro": "999",
            "ativo": "true",
        },
        follow_redirects=False,
    )

    assert response.status_code == status.HTTP_303_SEE_OTHER

    result = await db_session.execute(
        select(PerfilDizimista)
        .join(Usuario)
        .where(Usuario.nome == "Dizimista Com Registro")
    )
    perfil = result.scalar_one()

    assert perfil.numero_registro == 999


async def test_admin_cria_dizimista_com_numero_registro_duplicado(
    async_client: AsyncClient, db_session, admin_factory, igreja_factory
):
    admin = await _login_admin(async_client, db_session, admin_factory)
    igreja = await igreja_factory(db_session, paroquia_id=admin.paroquia_id)

    # Cria primeiro dizimista com numero 777
    await async_client.post(
        "/usuarios/novo",
        data={
            "nome": "Primeiro Dizimista",
            "perfil": "dizimista",
            "igreja_id": str(igreja.id),
            "numero_registro": "777",
            "ativo": "true",
        },
        follow_redirects=False,
    )

    # Tenta criar segundo com o mesmo numero
    response = await async_client.post(
        "/usuarios/novo",
        data={
            "nome": "Segundo Dizimista",
            "perfil": "dizimista",
            "igreja_id": str(igreja.id),
            "numero_registro": "777",
            "ativo": "true",
        },
        follow_redirects=False,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "número de registro" in response.text.lower()
    assert "já está em uso por outro dizimista" in response.text.lower()

async def test_admin_cria_administrador_exige_email_senha_e_paroquia(
    async_client: AsyncClient, db_session, admin_factory
):
    await _login_admin(async_client, db_session, admin_factory)

    response = await async_client.post(
        "/usuarios/novo",
        data={
            "nome": "Admin Sem Dados",
            "perfil": "administrador",
        },
        follow_redirects=False,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "e-mail" in response.text.lower()
    assert "senha" in response.text.lower()
    assert "paroquia" in response.text.lower()
