import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def client():
    """Cliente HTTP assíncrono que conversa direto com a app, sem servidor real."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_home_status_code(client):
    """Verifica se a rota home retorna status 200 (sucesso)."""
    response = await client.get("/")
    assert response.status_code == 200


async def test_home_content_type(client):
    """Verifica se a resposta é HTML."""
    response = await client.get("/")
    assert "text/html" in response.headers["content-type"]


async def test_home_contains_title(client):
    """Verifica se o título da página está presente no HTML retornado."""
    response = await client.get("/")
    assert "Gerenciador de Dízimo" in response.text


async def test_home_contains_welcome_message(client):
    """Verifica se a mensagem de bem-vindo está presente."""
    response = await client.get("/")
    assert "Bem-vindo" in response.text


async def test_home_contains_docs_link(client):
    """Verifica se o link para a documentação da API está presente."""
    response = await client.get("/")
    assert 'href="/docs"' in response.text
