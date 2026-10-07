import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.security import hash_senha
from app.db.session import get_db
from app.main import app
from app.models.security_log import SecurityLog
from app.models.usuario import PerfilUsuario, Usuario

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def client(db_session):
    """Cliente HTTP com override do get_db para usar a sessão de teste."""

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def usuario_dizimista(db_session):
    usuario = Usuario(
        nome="Dizimista Teste",
        email="dizimista@teste.com",
        senha_hash=hash_senha("senha123"),
        perfil=PerfilUsuario.DIZIMISTA,
        ativo=True,
    )
    db_session.add(usuario)
    await db_session.commit()
    await db_session.refresh(usuario)
    return usuario


async def test_login_sucesso(client, usuario_dizimista):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": usuario_dizimista.email, "senha": "senha123"},
    )

    assert response.status_code == 200
    dados = response.json()
    assert "access_token" in dados
    assert dados["token_type"] == "bearer"


async def test_login_senha_incorreta(client, usuario_dizimista):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": usuario_dizimista.email, "senha": "senha_errada"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciais inválidas."


async def test_login_email_inexistente(client):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "naoexiste@teste.com", "senha": "qualquer"},
    )

    assert response.status_code == 401


async def test_login_usuario_inativo(client, db_session):
    usuario = Usuario(
        nome="Inativo",
        email="inativo@teste.com",
        senha_hash=hash_senha("senha123"),
        perfil=PerfilUsuario.DIZIMISTA,
        ativo=False,
    )
    db_session.add(usuario)
    await db_session.commit()

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": usuario.email, "senha": "senha123"},
    )

    assert response.status_code == 403
    assert "desativada" in response.json()["detail"].lower()


async def test_me_com_token_valido(client, usuario_dizimista):
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": usuario_dizimista.email, "senha": "senha123"},
    )
    token = login_response.json()["access_token"]

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    dados = response.json()
    assert dados["email"] == usuario_dizimista.email


async def test_me_sem_token(client):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_me_token_invalido(client):
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer token_invalido_xyz"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Não foi possível validar as credenciais."


async def test_logout_com_token_valido(client, usuario_dizimista):
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": usuario_dizimista.email, "senha": "senha123"},
    )
    token = login_response.json()["access_token"]

    response = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204
    assert response.content == b""


async def test_logout_sem_token(client):
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 401


async def test_logout_token_invalido(client):
    response = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": "Bearer token_invalido_xyz"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Não foi possível validar as credenciais."


async def test_logout_registra_evento_em_security_log(
    client, db_session, usuario_dizimista
):

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": usuario_dizimista.email, "senha": "senha123"},
    )
    token = login_response.json()["access_token"]

    await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )

    resultado = await db_session.execute(
        select(SecurityLog)
        .where(SecurityLog.usuario_id == usuario_dizimista.id)
        .where(SecurityLog.evento == "logout")
    )
    log = resultado.scalar_one_or_none()

    assert log is not None
    assert log.evento == "logout"
