from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_home_status_code():
    """Verifica se a rota home retorna status 200 (sucesso)."""
    response = client.get("/")
    assert response.status_code == 200


def test_home_content_type():
    """Verifica se a resposta é HTML."""
    response = client.get("/")
    assert "text/html" in response.headers["content-type"]


def test_home_contains_title():
    """Verifica se o título da página está presente no HTML retornado."""
    response = client.get("/")
    assert "Gerenciador de Dízimo" in response.text


def test_home_contains_welcome_message():
    """Verifica se a mensagem de bem-vindo está presente."""
    response = client.get("/")
    assert "Bem-vindo" in response.text


def test_home_contains_docs_link():
    """Verifica se o link para a documentação da API está presente."""
    response = client.get("/")
    assert 'href="/docs"' in response.text
