"""
Testes E2E (navegador real) para as views de cadastro, login e logout.

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
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

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
APP_BASE_URL="http://webserver:8000"


# Engine assíncrona apontando para o MESMO banco de teste do conftest.py
# ({settings.postgres_db}_test). O container "app", ao rodar esses testes,
# também deve estar conectado a esse banco (ver docker-compose.selenium.yml).
_engine_test = create_async_engine(TEST_DATABASE_URL, echo=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _garantir_banco_de_teste_migrado():
    """
    Garante, de forma independente dos testes de integração, que o banco
    "{settings.postgres_db}_test" existe e está com as migrações Alembic
    atualizadas antes de qualquer teste Selenium rodar.

    Reaproveita exatamente a mesma lógica usada pela fixture `engine` do
    conftest.py, evitando duplicação de regras de criação/migração.
    """
    await _ensure_test_database_exists()

    sync_test_url = TEST_DATABASE_URL.replace("+asyncpg", "")
    await asyncio.to_thread(_run_alembic_upgrade, sync_test_url)

    yield

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
    """Aprova diretamente no banco o cadastro recém-criado via formulário,
    simulando a validação do administrador (UC04), para permitir login."""
    async with _engine_test.begin() as conn:
        await conn.execute(
            text(
                """
                UPDATE perfil_dizimista
                SET status_cadastro = 'APROVADO'
                WHERE usuario_id = (SELECT id FROM usuario WHERE email = :email)
                """
            ),
            {"email": email},
        )


def _email_unico() -> str:
    # Domínio sintaticamente válido e NÃO reservado pela IANA/RFC 2606,
    # já que a validação roda no processo da aplicação (uvicorn), um
    # processo separado do pytest — portanto qualquer monkeypatch feito
    # aqui no lado do teste não tem efeito algum no servidor.
    return f"teste.selenium.{uuid.uuid4().hex[:10]}@gmail.com"


class TestCadastroUsuario:
    async def test_cadastro_dizimista_com_dados_validos(self, driver):
        email = _email_unico()
        driver.get(f"{APP_BASE_URL}/usuarios/novo")

        driver.find_element(By.ID, "nome").send_keys("Usuário Selenium")
        driver.find_element(By.ID, "email").send_keys(email)
        driver.find_element(By.ID, "senha").send_keys("senha_valida123")
        driver.find_element(By.ID, "confirmar_senha").send_keys("senha_valida123")

        select_perfil = driver.find_element(By.ID, "perfil")
        select_perfil.find_element(
            By.CSS_SELECTOR, "option[value='dizimista']"
        ).click()

        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        WebDriverWait(driver, 5).until(
            lambda d: d.current_url != f"{APP_BASE_URL}/usuarios/novo"
        )
        assert driver.current_url != f"{APP_BASE_URL}/usuarios/novo"

    async def test_cadastro_com_senhas_diferentes_mostra_erro(self, driver):
        driver.get(f"{APP_BASE_URL}/usuarios/novo")

        driver.find_element(By.ID, "nome").send_keys("Usuário Inválido")
        driver.find_element(By.ID, "email").send_keys(_email_unico())
        driver.find_element(By.ID, "senha").send_keys("senha_valida123")
        driver.find_element(By.ID, "confirmar_senha").send_keys("outra_senha456")

        select_perfil = driver.find_element(By.ID, "perfil")
        select_perfil.find_element(
            By.CSS_SELECTOR, "option[value='dizimista']"
        ).click()

        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        alerta = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".alert-danger"))
        )
        assert alerta.is_displayed()


class TestLoginELogout:
    async def _criar_e_aprovar_dizimista(self, driver) -> tuple[str, str]:
        email = _email_unico()
        senha = "senha_valida123"

        driver.get(f"{APP_BASE_URL}/usuarios/novo")
        driver.find_element(By.ID, "nome").send_keys("Usuário Login")
        driver.find_element(By.ID, "email").send_keys(email)
        driver.find_element(By.ID, "senha").send_keys(senha)
        driver.find_element(By.ID, "confirmar_senha").send_keys(senha)
        driver.find_element(By.ID, "perfil").find_element(
            By.CSS_SELECTOR, "option[value='dizimista']"
        ).click()
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        WebDriverWait(driver, 5).until(
            lambda d: d.current_url != f"{APP_BASE_URL}/usuarios/novo"
        )
        await _aprovar_dizimista(email)
        return email, senha

    async def test_login_com_credenciais_validas_redireciona_para_home(self, driver):
        email, senha = await self._criar_e_aprovar_dizimista(driver)

        driver.get(f"{APP_BASE_URL}/auth/login")
        driver.find_element(By.ID, "email").send_keys(email)
        driver.find_element(By.ID, "senha").send_keys(senha)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        WebDriverWait(driver, 5).until(EC.url_to_be(f"{APP_BASE_URL}/"))

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

        driver.get(f"{APP_BASE_URL}/auth/login")
        driver.find_element(By.ID, "email").send_keys(email)
        driver.find_element(By.ID, "senha").send_keys(senha)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        WebDriverWait(driver, 5).until(EC.url_to_be(f"{APP_BASE_URL}/"))

        link_sair = driver.find_element(By.LINK_TEXT, "Sair")
        link_sair.click()

        WebDriverWait(driver, 5).until(EC.url_to_be(f"{APP_BASE_URL}/"))

        cookies = {c["name"] for c in driver.get_cookies()}
        assert "access_token" not in cookies

        link_login = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.LINK_TEXT, "Login"))
        )
        assert link_login.is_displayed()

def test_debug_chrome_policy(driver):
    driver.get("chrome://policy")
    import time
    time.sleep(1)
    print("\n\n===== CHROME POLICY PAGE SOURCE =====\n")
    print(driver.page_source)
    print("\n===== FIM =====\n")


def test_debug_get_por_ip(driver):
    driver.get("http://172.19.0.4:8000/usuarios/novo")
    assert "usuarios/novo" in driver.current_url


async def _aprovar_dizimista(email: str) -> None:
    """Aprova diretamente no banco o cadastro recém-criado via formulário,
    simulando a validação do administrador (UC04), para permitir login."""
    async with _engine_test.begin() as conn:
        await conn.execute(
            text(
                """
                UPDATE perfil_dizimista
                SET status_cadastro = 'APROVADO'
                WHERE usuario_id = (SELECT id FROM usuario WHERE email = :email)
                """
            ),
            {"email": email},
        )