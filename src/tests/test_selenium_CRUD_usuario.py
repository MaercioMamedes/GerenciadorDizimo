"""
Testes E2E (navegador real) para as views de cadastro, login, logout,
detalhes, listagem, edição e exclusão de usuário.

Pré-requisitos:
    - docker-compose --profile dev up -d   (sobe também o container "selenium")
    - app rodando e acessível, dentro da rede Docker, apontando para o MESMO
      banco de teste usado aqui (ver docker-compose.selenium.yml)
    - container "selenium" acessível em http://selenium:4444/wd/hub

Esses testes usam o banco "{settings.postgres_db}_test" — o mesmo banco
dedicado aos testes de integração (ver conftest.py) — mas garantem de forma
INDEPENDENTE que ele existe e está migrado, reaproveitando as funções do
conftest, sem exigir que os testes de integração sejam executados antes.

Marcados com `@pytest.mark.selenium` para serem executados separadamente
dos testes de unidade/integração padrão:

    pytest -m selenium
"""

import asyncio
import os
import uuid

import pytest
import pytest_asyncio
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.client_config import ClientConfig
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import create_async_engine

from app.models.usuario import PerfilUsuario, Usuario
from selenium import webdriver
from tests.conftest import (
    TEST_DATABASE_URL,
    _ensure_test_database_exists,
    _run_alembic_upgrade,
)

pytestmark = pytest.mark.selenium

SELENIUM_REMOTE_URL = os.environ.get(
    "SELENIUM_REMOTE_URL", "http://selenium:4444/wd/hub"
)
APP_BASE_URL = "http://webserver:8000"


# Engine assíncrona apontando para o MESMO banco de teste do conftest.py
# ({settings.postgres_db}_test). O container "app", ao rodar esses testes,
# também deve estar conectado a esse banco (ver docker-compose.selenium.yml).
_engine_test = create_async_engine(TEST_DATABASE_URL, echo=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _garantir_banco_de_teste_migrado():
    await _ensure_test_database_exists()

    sync_test_url = TEST_DATABASE_URL.replace("+asyncpg", "")
    await asyncio.to_thread(_run_alembic_upgrade, sync_test_url)

    # Garante um ponto de partida limpo e determinístico a cada execução
    # da suíte Selenium, já que a exclusão de usuário é soft delete (as
    # linhas nunca são removidas) e o volume do Postgres persiste entre
    # execuções do `make test-selenium`.
    async with _engine_test.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE usuario CASCADE"))

    # Limpeza acontece DEPOIS da suíte, não antes:
    # mantém o estado do banco inspecionável caso algum teste falhe,
    # e começa cada execução "do zero" apenas na próxima rodada.
    yield

    async with _engine_test.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE usuario CASCADE"))

    await _engine_test.dispose()


@pytest.fixture
def driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(
        "--disable-features=HttpsUpgrades,HttpsFirstModeV2,"
        "HttpsFirstModeV2ForEngagedSites,HttpsFirstBalancedMode,"
        "HttpsFirstBalancedModeAutoEnable,HttpsFirstModeIncognito"
    )
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--allow-running-insecure-content")
    options.add_argument(
        "--unsafely-treat-insecure-origin-as-secure="
        f"{APP_BASE_URL},http://app:8000,http://app.local:8000"
    )
    options.set_capability("acceptInsecureCerts", True)

    client_config = ClientConfig(
        remote_server_addr=SELENIUM_REMOTE_URL,
        timeout=20,
    )

    navegador = webdriver.Remote(
        command_executor=SELENIUM_REMOTE_URL,
        options=options,
        client_config=client_config,
    )
    navegador.set_page_load_timeout(15)
    navegador.implicitly_wait(2)
    navegador.set_window_size(1920, 1080)  # define o tamanho DEPOIS da sessão criada
    yield navegador
    navegador.quit()


async def _aprovar_dizimista(email: str) -> None:
    """Ativa diretamente no banco o usuário recém-criado via formulário,
    simulando a validação do administrador (UC04), para permitir login."""
    async with _engine_test.begin() as conn:
        await conn.execute(
            text(
                """
                UPDATE usuario
                SET ativo = true
                WHERE email = :email
                """
            ),
            {"email": email},
        )


async def _tornar_administrador(email: str) -> None:
    """Promove o usuário a administrador diretamente no banco, necessário
    para os testes que exigem acesso às telas restritas (lista/detalhes/
    edição/exclusão de outros usuários).

    Usa SQLAlchemy Core (não SQL raw com string literal) para que o
    próprio dialect do asyncpg converta corretamente o enum Python para o
    tipo nativo `perfil_usuario_enum` do Postgres, evitando o mismatch
    entre o `.value` do enum e o label realmente usado na coluna.
    """
    async with _engine_test.begin() as conn:
        await conn.execute(
            update(Usuario)
            .where(Usuario.email == email)
            .values(perfil=PerfilUsuario.ADMINISTRADOR, ativo=True)
        )


def _email_unico() -> str:
    # Domínio sintaticamente válido e NÃO reservado pela IANA/RFC 2606,
    # já que a validação roda no processo da aplicação (uvicorn), um
    # processo separado do pytest — portanto qualquer monkeypatch feito
    # aqui no lado do teste não tem efeito algum no servidor.
    return f"teste.selenium.{uuid.uuid4().hex[:10]}@gmail.com"


def _login(driver, email: str, senha: str) -> None:
    driver.get(f"{APP_BASE_URL}/auth/login")
    driver.find_element(By.ID, "email").send_keys(email)
    driver.find_element(By.ID, "senha").send_keys(senha)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    WebDriverWait(driver, 5).until(EC.url_to_be(f"{APP_BASE_URL}/"))


def _cadastrar_dizimista(driver, nome: str, email: str, senha: str) -> None:
    driver.get(f"{APP_BASE_URL}/usuarios/novo")
    driver.find_element(By.ID, "nome").send_keys(nome)
    driver.find_element(By.ID, "email").send_keys(email)
    driver.find_element(By.ID, "senha").send_keys(senha)
    driver.find_element(By.ID, "confirmar_senha").send_keys(senha)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    WebDriverWait(driver, 5).until(
        lambda d: d.current_url != f"{APP_BASE_URL}/usuarios/novo"
    )


class TestCadastroUsuario:
    async def test_cadastro_dizimista_com_dados_validos(self, driver):
        email = _email_unico()
        _cadastrar_dizimista(driver, "Usuário Selenium", email, "senha_valida123")
        assert driver.current_url != f"{APP_BASE_URL}/usuarios/novo"

    async def test_cadastro_com_senhas_diferentes_mostra_erro(self, driver):
        driver.get(f"{APP_BASE_URL}/usuarios/novo")

        driver.find_element(By.ID, "nome").send_keys("Usuário Inválido")
        driver.find_element(By.ID, "email").send_keys(_email_unico())
        driver.find_element(By.ID, "senha").send_keys("senha_valida123")
        driver.find_element(By.ID, "confirmar_senha").send_keys("outra_senha456")

        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        alerta = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".alert-danger"))
        )
        assert alerta.is_displayed()


class TestLoginELogout:
    async def _criar_e_aprovar_dizimista(self, driver) -> tuple[str, str]:
        email = _email_unico()
        senha = "senha_valida123"
        _cadastrar_dizimista(driver, "Usuário Login", email, senha)
        await _aprovar_dizimista(email)
        return email, senha

    async def test_login_com_credenciais_validas_redireciona_para_home(self, driver):
        email, senha = await self._criar_e_aprovar_dizimista(driver)
        _login(driver, email, senha)

        cookies = {c["name"] for c in driver.get_cookies()}
        assert "access_token" in cookies

        link_sair = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.LINK_TEXT, "Sair"))
        )
        assert link_sair.is_displayed()

    async def test_login_com_credenciais_invalidas_mostra_erro(self, driver):
        driver.get(f"{APP_BASE_URL}/auth/login")
        driver.find_element(By.ID, "email").send_keys("naoexiste@selenium.local")
        driver.find_element(By.ID, "senha").send_keys("qualquersenha")
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        alerta = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".alert-danger"))
        )
        assert "inválid" in alerta.text.lower()

    async def test_logout_remove_sessao_e_redireciona(self, driver):
        email, senha = await self._criar_e_aprovar_dizimista(driver)
        _login(driver, email, senha)

        link_sair = driver.find_element(By.LINK_TEXT, "Sair")
        link_sair.click()

        WebDriverWait(driver, 5).until(EC.url_to_be(f"{APP_BASE_URL}/"))

        cookies = {c["name"] for c in driver.get_cookies()}
        assert "access_token" not in cookies

        link_login = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.LINK_TEXT, "Login"))
        )
        assert link_login.is_displayed()


class TestListaEDetalhesUsuario:
    async def _criar_admin_logado(self, driver) -> tuple[str, str]:
        email = _email_unico()
        senha = "senha_valida123"
        _cadastrar_dizimista(driver, "Admin Selenium", email, senha)
        await _tornar_administrador(email)
        _login(driver, email, senha)
        return email, senha

    async def test_lista_usuarios_exibe_usuario_cadastrado(self, driver):
        await self._criar_admin_logado(driver)

        email_dizimista = _email_unico()
        _cadastrar_dizimista(driver, "Fulano da Lista", email_dizimista, "senha_valida123")

        driver.get(f"{APP_BASE_URL}/usuarios")
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table"))
        )
        assert email_dizimista in driver.page_source

    async def test_filtro_por_perfil_administrador_na_lista(self, driver):
        email_admin, _ = await self._criar_admin_logado(driver)

        driver.get(f"{APP_BASE_URL}/usuarios?perfil=administrador")
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table"))
        )
        assert email_admin in driver.page_source

    async def test_acessar_detalhes_de_usuario_a_partir_da_lista(self, driver):
        await self._criar_admin_logado(driver)

        email_dizimista = _email_unico()
        _cadastrar_dizimista(driver, "Detalhe Selenium", email_dizimista, "senha_valida123")

        driver.get(f"{APP_BASE_URL}/usuarios")
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.LINK_TEXT, "Detalhes"))
        )

        linha = driver.find_element(
            By.XPATH, f"//tr[td[contains(text(), '{email_dizimista}')]]"
        )
        linha.find_element(By.LINK_TEXT, "Detalhes").click()

        WebDriverWait(driver, 5).until(
            EC.text_to_be_present_in_element((By.TAG_NAME, "body"), email_dizimista)
        )
        assert "Detalhes do Usuário" in driver.page_source
        assert email_dizimista in driver.page_source


class TestEdicaoUsuario:
    async def _criar_admin_logado(self, driver) -> tuple[str, str]:
        email = _email_unico()
        senha = "senha_valida123"
        _cadastrar_dizimista(driver, "Admin Edicao", email, senha)
        await _tornar_administrador(email)
        _login(driver, email, senha)
        return email, senha

    async def test_editar_usuario_atualiza_nome_e_persiste(self, driver):
        await self._criar_admin_logado(driver)

        email_dizimista = _email_unico()
        _cadastrar_dizimista(driver, "Nome Original", email_dizimista, "senha_valida123")

        driver.get(f"{APP_BASE_URL}/usuarios")
        linha = WebDriverWait(driver, 5).until(
            lambda d: d.find_element(
                By.XPATH, f"//tr[td[contains(text(), '{email_dizimista}')]]"
            )
        )
        linha.find_element(By.LINK_TEXT, "Editar").click()

        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "nome"))
        )

        campo_nome = driver.find_element(By.ID, "nome")
        campo_nome.clear()
        campo_nome.send_keys("Nome Atualizado via Selenium")

        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        WebDriverWait(driver, 5).until(EC.url_to_be(f"{APP_BASE_URL}/usuarios"))
        assert "Nome Atualizado via Selenium" in driver.page_source

class TestExclusaoUsuario:
    async def _criar_admin_logado(self, driver) -> tuple[str, str]:
        email = _email_unico()
        senha = "senha_valida123"
        _cadastrar_dizimista(driver, "Admin Exclusao", email, senha)
        await _tornar_administrador(email)
        _login(driver, email, senha)
        return email, senha

    async def test_admin_exclui_outro_usuario_e_permanece_logado(self, driver):
        await self._criar_admin_logado(driver)

        email_dizimista = _email_unico()
        _cadastrar_dizimista(driver, "Vai Ser Excluido", email_dizimista, "senha_valida123")

        driver.get(f"{APP_BASE_URL}/usuarios?tamanho_pagina=100")
        linha = WebDriverWait(driver, 5).until(
            lambda d: d.find_element(
                By.XPATH, f"//tr[td[contains(text(), '{email_dizimista}')]]"
            )
        )
        linha.find_element(By.LINK_TEXT, "Detalhes").click()

        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "button[type='submit']"))
        )

        # Confirma o window.confirm() do onsubmit do formulário de exclusão
        driver.execute_script(
            "window.confirm = function() { return true; };"
        )
        driver.find_element(By.CSS_SELECTOR, "form button.btn-outline-danger").click()



        WebDriverWait(driver, 5).until(EC.url_to_be(f"{APP_BASE_URL}/usuarios"))

        # Admin continua autenticado: a exclusão foi de OUTRO usuário.
        cookies = {c["name"] for c in driver.get_cookies()}
        assert "access_token" in cookies

        # Usuário excluído não deve mais conseguir logar.
        driver.delete_all_cookies()
        driver.get(f"{APP_BASE_URL}/auth/login")
        driver.find_element(By.ID, "email").send_keys(email_dizimista)
        driver.find_element(By.ID, "senha").send_keys("senha_valida123")
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        alerta = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".alert-danger"))
        )
        assert alerta.is_displayed()



