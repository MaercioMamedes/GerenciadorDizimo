"""
Testes E2E (navegador real) para as views de cadastro, login, logout,
detalhes, listagem, edição e exclusão de usuário.

Pré-requisitos:
    - docker-compose --profile dev up -d
    - app rodando e acessível em http://webserver:8000
    - container selenium em http://selenium:4444/wd/hub

    pytest -m selenium
"""

import asyncio
import os
import uuid

import pytest
import pytest_asyncio
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.client_config import ClientConfig
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.igreja import Igreja
from app.models.paroquia import Paroquia
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

_PAROQUIA_ID: str | None = None
_IGREJA_ID: str | None = None

_engine_test = create_async_engine(TEST_DATABASE_URL, echo=False)
_async_session_maker = sessionmaker(
    _engine_test, class_=AsyncSession, expire_on_commit=False
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _garantir_banco_de_teste_migrado():
    """
    Garante banco de teste migrado e cria uma paróquia + igreja matriz
    de teste antes de qualquer teste Selenium.
    """
    await _ensure_test_database_exists()

    sync_test_url = TEST_DATABASE_URL.replace("+asyncpg", "")
    await asyncio.to_thread(_run_alembic_upgrade, sync_test_url)

    global _PAROQUIA_ID, _IGREJA_ID

    async with _async_session_maker() as session:
        await session.execute(text("TRUNCATE TABLE usuario CASCADE"))

        paroquia = (
            await session.execute(select(Paroquia).limit(1))
        ).scalar_one_or_none()

        if paroquia is None:
            paroquia = Paroquia(cnpj="12.345.678/0001-90")
            session.add(paroquia)
            await session.flush()

        igreja = (
            await session.execute(
                select(Igreja).where(Igreja.paroquia_id == paroquia.id).limit(1)
            )
        ).scalar_one_or_none()

        if igreja is None:
            igreja = Igreja(
                nome="Igreja Matriz Selenium",
                endereco="Rua dos Testes, 1",
                is_matriz=True,
                paroquia_id=paroquia.id,
            )
            session.add(igreja)

        await session.commit()
        await session.refresh(paroquia)
        await session.refresh(igreja)

        _PAROQUIA_ID = str(paroquia.id)
        _IGREJA_ID = str(igreja.id)

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
    navegador.set_window_size(1920, 1080)
    yield navegador
    navegador.quit()


# ---------------------------------------------------------------------------
# Helpers de banco
# ---------------------------------------------------------------------------


async def _aprovar_dizimista(email: str) -> None:
    async with _engine_test.begin() as conn:
        await conn.execute(
            text("UPDATE usuario SET ativo = true WHERE email = :email"),
            {"email": email},
        )


async def _tornar_administrador(email: str) -> None:
    async with _engine_test.begin() as conn:
        await conn.execute(
            update(Usuario)
            .where(Usuario.email == email)
            .values(perfil=PerfilUsuario.ADMINISTRADOR, ativo=True)
        )


# ---------------------------------------------------------------------------
# Helpers de UI
# ---------------------------------------------------------------------------


def _email_unico() -> str:
    return f"teste.selenium.{uuid.uuid4().hex[:10]}@gmail.com"


def _page_debug(driver, max_chars: int = 3000) -> str:
    """Retorna URL e trecho do HTML para diagnóstico de falhas."""
    return f"""\nURL: {driver.current_url}\n
            PAGE SOURCE (truncado):\n{driver.page_source[:max_chars]}"""


def _aguardar_carregamento_pagina(driver, timeout: int = 10) -> None:
    """
    Aguarda o documento estar completamente carregado e o JS inicial executado.
    """
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )


def _clicar_elemento(driver, locator_or_element, timeout: int = 10) -> None:
    """
    Clica em um elemento. Aceita locator (tuple) ou WebElement.
    Usa clique nativo, depois ActionChains, depois JavaScript.
    """
    if isinstance(locator_or_element, tuple):
        elemento = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(locator_or_element)
        )
    else:
        elemento = locator_or_element

    driver.execute_script(
        "arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});",
        elemento,
    )

    try:
        WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(elemento))
        elemento.click()
        return
    except Exception:
        pass

    try:
        ActionChains(driver).move_to_element(elemento).pause(0.2).click().perform()
        return
    except Exception:
        pass

    driver.execute_script("arguments[0].click();", elemento)


def _clicar_submit(driver) -> None:
    _clicar_elemento(driver, (By.CSS_SELECTOR, "button[type='submit']"))


def _preencher_campos_comuns(driver, nome: str, email: str, senha: str | None) -> None:
    driver.find_element(By.ID, "nome").send_keys(nome)
    driver.find_element(By.ID, "email").send_keys(email)
    if senha:
        driver.find_element(By.ID, "senha").send_keys(senha)
        driver.find_element(By.ID, "confirmar_senha").send_keys(senha)


def _existe_elemento(driver, by, value) -> bool:
    """Verifica se um elemento existe no DOM sem levantar exceção."""
    try:
        driver.find_element(by, value)
        return True
    except NoSuchElementException:
        return False


def _selecionar_perfil(driver, perfil: str) -> None:
    """
    Seleciona o perfil no formulário administrativo.
    No cadastro público o campo não existe (é input hidden); nesse caso,
    a função não faz nada.
    """
    if not _existe_elemento(driver, By.ID, "perfil"):
        return

    select_perfil = Select(
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "perfil"))
        )
    )
    select_perfil.select_by_value(perfil)

    # Dispara explicitamente o onchange para garantir que o JS reaja no Selenium
    driver.execute_script(
        "arguments[0].dispatchEvent(new Event('change', { bubbles: true }));",
        driver.find_element(By.ID, "perfil"),
    )


def _garantir_campos_dizimista_visiveis(driver) -> None:
    """
    Força a exibição dos campos de dizimista e remove o required do igreja_id
    via JS apenas quando necessário para testes específicos.
    """
    driver.execute_script("""
        const div = document.getElementById('campos-dizimista');
        if (div) {
            div.style.display = 'block';
            div.style.visibility = 'visible';
        }
    """)


def _selecionar_igreja(driver, igreja_id: str | None = None) -> None:
    igreja_id = igreja_id or _IGREJA_ID

    _garantir_campos_dizimista_visiveis(driver)

    select_igreja = Select(
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "igreja_id"))
        )
    )
    WebDriverWait(driver, 5).until(lambda _: len(select_igreja.options) > 1)

    # Garante que o option desejado existe antes de selecionar
    WebDriverWait(driver, 5).until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, f'#igreja_id option[value="{igreja_id}"]')
        )
    )
    select_igreja.select_by_value(igreja_id)


def _selecionar_paroquia(driver, paroquia_id: str | None = None) -> None:
    paroquia_id = paroquia_id or _PAROQUIA_ID

    # Aguarda o campo existir no DOM e força visibilidade
    campo = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "campo-paroquia"))
    )
    driver.execute_script(
        "arguments[0].style.display = 'block'; "
        "arguments[0].style.visibility = 'visible';",
        campo,
    )

    # Aguarda o fetch popular o select
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, f"#paroquia_id option[value='{paroquia_id}']")
        )
    )

    # Seleciona via JS para evitar stale element
    driver.execute_script(
        """
        const select = document.getElementById('paroquia_id');
        select.value = arguments[0];
        select.dispatchEvent(new Event('change', { bubbles: true }));
        """,
        paroquia_id,
    )



def _submeter_formulario(
    driver,
    timeout: int = 10,
    forcar: bool = False,
    esperar_redirecionamento: bool = True,
) -> None:
    """
    Clica em submit e aguarda a página sair do formulário.
    Se forcar=True, remove a validação HTML5 e dispara submit via JS,
    garantindo que o backend receba a requisição.

    Quando esperar_redirecionamento=False, não aguarda mudança de URL.
    Útil para testes que esperam mensagens de erro na mesma página (422).
    """
    url_formulario = driver.current_url

    if forcar:
        driver.execute_script("""
            const form = document.querySelector('form');
            if (form) {
                form.setAttribute('novalidate', 'novalidate');
                HTMLFormElement.prototype.submit.call(form);
            }
        """)
    else:
        _clicar_submit(driver)

    if not esperar_redirecionamento:
        return

    try:
        WebDriverWait(driver, timeout).until(lambda d: d.current_url != url_formulario)
    except TimeoutException as exc:
        # Fallback final
        driver.execute_script("""
            const form = document.querySelector('form');
            if (form) {
                form.setAttribute('novalidate', 'novalidate');
                HTMLFormElement.prototype.submit.call(form);
            }
        """)
        try:
            WebDriverWait(driver, 3).until(lambda d: d.current_url != url_formulario)
        except TimeoutException:
            raise TimeoutException(
                f"Formulário não redirecionou após submit.{_page_debug(driver)}"
            ) from exc


def _aguardar_alerta_erro(driver, timeout: int = 10) -> None:
    """
    Aguarda .alert-danger. Se não aparecer, levanta erro com URL e HTML.
    """
    try:
        WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".alert-danger"))
        )
    except TimeoutException as exc:
        raise TimeoutException(
            f"Não apareceu .alert-danger após submit.{_page_debug(driver)}"
        ) from exc


def _aguardar_visivel(driver, by, value, timeout: int = 10) -> None:
    WebDriverWait(driver, timeout).until(
        EC.visibility_of_element_located((by, value))
    )


def _cadastrar_dizimista(
    driver,
    nome: str,
    email: str,
    senha: str,
    igreja_id: str | None = None,
) -> None:
    driver.get(f"{APP_BASE_URL}/usuarios/novo")
    _aguardar_carregamento_pagina(driver)

    _preencher_campos_comuns(driver, nome, email, senha)

    # No cadastro público #perfil não existe (input hidden). No cadastro por
    # admin, garantimos que o formulário esteja no perfil Dizimista.
    _selecionar_perfil(driver, "dizimista")

    _selecionar_igreja(driver, igreja_id)
    _submeter_formulario(driver)


def _cadastrar_administrador(
    driver,
    nome: str,
    email: str,
    senha: str,
    paroquia_id: str | None = None,
    tambem_dizimista: bool = False,
    igreja_id: str | None = None,
) -> None:
    driver.get(f"{APP_BASE_URL}/usuarios/novo")
    _aguardar_carregamento_pagina(driver)

    _preencher_campos_comuns(driver, nome, email, senha)

    _selecionar_perfil(driver, "administrador")
    _selecionar_paroquia(driver, paroquia_id)

    if tambem_dizimista:
        checkbox = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "tambem_dizimista"))
        )
        _clicar_elemento(driver, checkbox)
        _selecionar_igreja(driver, igreja_id)

    _submeter_formulario(driver)


def _login(driver, email: str, senha: str) -> None:
    driver.get(f"{APP_BASE_URL}/auth/login")
    _aguardar_carregamento_pagina(driver)

    driver.find_element(By.ID, "email").send_keys(email)
    driver.find_element(By.ID, "senha").send_keys(senha)
    _clicar_submit(driver)

    WebDriverWait(driver, 8).until(EC.url_to_be(f"{APP_BASE_URL}/"))


async def _criar_admin_logado(driver) -> tuple[str, str]:
    email = _email_unico()
    senha = "senha_valida123"
    _cadastrar_dizimista(driver, "Admin Selenium", email, senha)
    await _tornar_administrador(email)
    _login(driver, email, senha)
    return email, senha


def _linha_usuario(driver, email: str):
    """Localiza a linha do usuário na tabela, com scroll e espera."""
    xpath = f"//tr[td[contains(text(), '{email}')]]"
    linha = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, xpath))
    )
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", linha)
    return linha


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------


class TestCadastroUsuario:
    async def test_cadastro_dizimista_com_dados_validos(self, driver):
        email = _email_unico()
        _cadastrar_dizimista(driver, "Usuário Selenium", email, "senha_valida123")

        assert (
            driver.current_url.startswith(f"{APP_BASE_URL}/auth/login")
            or driver.current_url == f"{APP_BASE_URL}/usuarios"
        )

    async def test_cadastro_com_senhas_diferentes_mostra_erro(self, driver):
        driver.get(f"{APP_BASE_URL}/usuarios/novo")
        _aguardar_carregamento_pagina(driver)

        _preencher_campos_comuns(
            driver, "Usuário Inválido", _email_unico(), "senha_valida123"
        )
        driver.find_element(By.ID, "confirmar_senha").clear()
        driver.find_element(By.ID, "confirmar_senha").send_keys("outra_senha456")
        _selecionar_igreja(driver)

        # Não aguarda redirecionamento: a view retorna 422 na mesma URL.
        _submeter_formulario(driver, forcar=True, esperar_redirecionamento=False)
        _aguardar_alerta_erro(driver)

    async def test_cadastro_publico_sem_igreja_nao_envia(self, driver):
        driver.get(f"{APP_BASE_URL}/usuarios/novo")
        _aguardar_carregamento_pagina(driver)

        _preencher_campos_comuns(
            driver, "Sem Igreja", _email_unico(), "senha_valida123"
        )

        # Força o envio ignorando validação HTML5 para testar o backend
        _submeter_formulario(driver, forcar=True, esperar_redirecionamento=False)

        _aguardar_alerta_erro(driver)
        alerta = driver.find_element(By.CSS_SELECTOR, ".alert-danger")
        assert "igreja" in alerta.text.lower()



class TestCadastroPorAdministrador:
    async def test_admin_cria_dizimista_ativo_sem_senha(self, driver):
        await _criar_admin_logado(driver)

        email = _email_unico()
        driver.get(f"{APP_BASE_URL}/usuarios/novo")
        _aguardar_carregamento_pagina(driver)

        driver.find_element(By.ID, "nome").send_keys("Dizimista Sem Acesso")
        driver.find_element(By.ID, "email").send_keys(email)
        _selecionar_igreja(driver)
        _clicar_submit(driver)

        WebDriverWait(driver, 8).until(EC.url_to_be(f"{APP_BASE_URL}/usuarios"))
        assert email in driver.page_source

    async def test_admin_cria_administrador_com_paroquia(self, driver):
        await _criar_admin_logado(driver)

        email = _email_unico()
        _cadastrar_administrador(driver, "Novo Admin", email, "senha_valida123")

        WebDriverWait(driver, 8).until(EC.url_to_be(f"{APP_BASE_URL}/usuarios"))
        assert email in driver.page_source

    async def test_admin_cria_administrador_sem_paroquia_mostra_erro(self, driver):
        await _criar_admin_logado(driver)

        email = _email_unico()
        driver.get(f"{APP_BASE_URL}/usuarios/novo")
        _aguardar_carregamento_pagina(driver)

        _preencher_campos_comuns(driver, "Admin Sem Paróquia", email, "senha_valida123")
        _selecionar_perfil(driver, "administrador")

        # Aguarda o campo paróquia aparecer (JS)
        _aguardar_visivel(driver, By.ID, "campo-paroquia")

        # Força o envio ignorando required do HTML5; não aguarda redirecionamento.
        _submeter_formulario(driver, forcar=True, esperar_redirecionamento=False)
        _aguardar_alerta_erro(driver)

        alerta = driver.find_element(By.CSS_SELECTOR, ".alert-danger")
        assert "paróquia" in alerta.text.lower()

    async def test_admin_cria_administrador_tambem_dizimista(self, driver):
        await _criar_admin_logado(driver)

        email = _email_unico()
        _cadastrar_administrador(
            driver,
            "Admin E Dizimista",
            email,
            "senha_valida123",
            tambem_dizimista=True,
        )

        WebDriverWait(driver, 8).until(EC.url_to_be(f"{APP_BASE_URL}/usuarios"))
        assert email in driver.page_source


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
        _aguardar_carregamento_pagina(driver)

        driver.find_element(By.ID, "email").send_keys("naoexiste@selenium.local")
        driver.find_element(By.ID, "senha").send_keys("qualquersenha")
        _clicar_submit(driver)

        _aguardar_alerta_erro(driver)

    async def test_logout_remove_sessao_e_redireciona(self, driver):
        email, senha = await self._criar_e_aprovar_dizimista(driver)
        _login(driver, email, senha)

        link_sair = driver.find_element(By.LINK_TEXT, "Sair")
        _clicar_elemento(driver, link_sair)

        WebDriverWait(driver, 8).until(EC.url_to_be(f"{APP_BASE_URL}/"))

        cookies = {c["name"] for c in driver.get_cookies()}
        assert "access_token" not in cookies

        link_login = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.LINK_TEXT, "Login"))
        )
        assert link_login.is_displayed()


class TestListaEDetalhesUsuario:
    async def test_lista_usuarios_exibe_usuario_cadastrado(self, driver):
        await _criar_admin_logado(driver)

        email_dizimista = _email_unico()
        _cadastrar_dizimista(
            driver, "Fulano da Lista", email_dizimista, "senha_valida123"
        )

        driver.get(f"{APP_BASE_URL}/usuarios?tamanho_pagina=100")
        WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table"))
        )
        assert email_dizimista in driver.page_source

    async def test_filtro_por_perfil_administrador_na_lista(self, driver):
        email_admin, _ = await _criar_admin_logado(driver)

        driver.get(f"{APP_BASE_URL}/usuarios?perfil=administrador&tamanho_pagina=100")
        WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table"))
        )
        assert email_admin in driver.page_source

    async def test_acessar_detalhes_de_usuario_a_partir_da_lista(self, driver):
        await _criar_admin_logado(driver)

        email_dizimista = _email_unico()
        _cadastrar_dizimista(
            driver, "Detalhe Selenium", email_dizimista, "senha_valida123"
        )

        driver.get(f"{APP_BASE_URL}/usuarios?tamanho_pagina=100")
        linha = _linha_usuario(driver, email_dizimista)
        _clicar_elemento(driver, linha.find_element(By.LINK_TEXT, "Detalhes"))

        # Aguarda a navegação de fato acontecer
        WebDriverWait(driver, 8).until(EC.url_contains("/usuarios/"))

        WebDriverWait(driver, 8).until(
            EC.text_to_be_present_in_element((By.TAG_NAME, "body"), email_dizimista)
        )
        assert "Detalhes do Usuário" in driver.page_source


class TestEdicaoUsuario:
    async def test_editar_usuario_atualiza_nome_e_persiste(self, driver):
        await _criar_admin_logado(driver)

        email_dizimista = _email_unico()
        _cadastrar_dizimista(driver, "Nome Original", email_dizimista, "senha_valida123")

        driver.get(f"{APP_BASE_URL}/usuarios?tamanho_pagina=100")
        linha = _linha_usuario(driver, email_dizimista)
        _clicar_elemento(driver, linha.find_element(By.LINK_TEXT, "Editar"))

        WebDriverWait(driver, 8).until(EC.url_contains("/editar"))
        _aguardar_visivel(driver, By.ID, "nome")

        campo_nome = driver.find_element(By.ID, "nome")
        campo_nome.clear()
        campo_nome.send_keys("Nome Atualizado via Selenium")

        _submeter_formulario(driver)

        WebDriverWait(driver, 8).until(EC.url_to_be(f"{APP_BASE_URL}/usuarios"))

        # Recarrega com paginação ampliada para garantir que o registro esteja visível
        driver.get(f"{APP_BASE_URL}/usuarios?tamanho_pagina=100")
        WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table"))
        )
        assert "Nome Atualizado via Selenium" in driver.page_source


    async def test_editar_usuario_para_administrador_sem_paroquia_mostra_erro(
        self, driver
    ):
        await _criar_admin_logado(driver)

        email_dizimista = _email_unico()
        _cadastrar_dizimista(
            driver, "Candidato Admin", email_dizimista, "senha_valida123"
        )

        driver.get(f"{APP_BASE_URL}/usuarios?tamanho_pagina=100")
        linha = _linha_usuario(driver, email_dizimista)
        _clicar_elemento(driver, linha.find_element(By.LINK_TEXT, "Editar"))

        WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.ID, "perfil"))
        )
        _selecionar_perfil(driver, "administrador")

        _aguardar_visivel(driver, By.ID, "campo-paroquia")

        # Força o envio ignorando required do HTML5; não aguarda redirecionamento.
        _submeter_formulario(driver, forcar=True, esperar_redirecionamento=False)
        _aguardar_alerta_erro(driver)

        alerta = driver.find_element(By.CSS_SELECTOR, ".alert-danger")
        assert "paróquia" in alerta.text.lower()

    async def test_editar_admin_marca_tambem_dizimista(self, driver):
        await _criar_admin_logado(driver)

        email_admin = _email_unico()
        _cadastrar_administrador(
            driver, "Admin Virando Dizimista", email_admin, "senha_valida123"
        )

        driver.get(f"{APP_BASE_URL}/usuarios?tamanho_pagina=100")
        linha = _linha_usuario(driver, email_admin)
        _clicar_elemento(driver, linha.find_element(By.LINK_TEXT, "Editar"))

        WebDriverWait(driver, 8).until(EC.url_contains("/editar"))

        # Garante que a paróquia esteja selecionada após o carregamento JS
        _selecionar_paroquia(driver)

        _aguardar_visivel(driver, By.ID, "tambem_dizimista")
        checkbox = driver.find_element(By.ID, "tambem_dizimista")
        _clicar_elemento(driver, checkbox)

        _aguardar_visivel(driver, By.ID, "campos-dizimista")
        _selecionar_igreja(driver)

        # Reforço: garante paróquia selecionada logo antes de submeter
        _selecionar_paroquia(driver)

        _submeter_formulario(driver)

        WebDriverWait(driver, 8).until(EC.url_to_be(f"{APP_BASE_URL}/usuarios"))

        driver.get(f"{APP_BASE_URL}/usuarios?tamanho_pagina=100")
        linha = _linha_usuario(driver, email_admin)
        _clicar_elemento(driver, linha.find_element(By.LINK_TEXT, "Detalhes"))

        WebDriverWait(driver, 8).until(EC.url_contains("/usuarios/"))
        WebDriverWait(driver, 8).until(
            EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Perfil de Dizimista")
        )
        assert "Igreja Matriz Selenium" in driver.page_source



class TestExclusaoUsuario:
    async def test_admin_exclui_outro_usuario_e_permanece_logado(self, driver):
        await _criar_admin_logado(driver)

        email_dizimista = _email_unico()
        _cadastrar_dizimista(
            driver, "Vai Ser Excluido", email_dizimista, "senha_valida123"
        )

        driver.get(f"{APP_BASE_URL}/usuarios?tamanho_pagina=100")
        linha = _linha_usuario(driver, email_dizimista)
        _clicar_elemento(driver, linha.find_element(By.LINK_TEXT, "Detalhes"))

        WebDriverWait(driver, 8).until(EC.url_contains("/usuarios/"))
        _aguardar_visivel(driver, By.CSS_SELECTOR, "button[type='submit']")

        driver.execute_script("window.confirm = function() { return true; };")

        botao_excluir = driver.find_element(
            By.CSS_SELECTOR, "form button.btn-outline-danger"
        )
        _clicar_elemento(driver, botao_excluir)

        WebDriverWait(driver, 8).until(EC.url_to_be(f"{APP_BASE_URL}/usuarios"))

        cookies = {c["name"] for c in driver.get_cookies()}
        assert "access_token" in cookies

        driver.delete_all_cookies()
        driver.get(f"{APP_BASE_URL}/auth/login")
        _aguardar_carregamento_pagina(driver)

        driver.find_element(By.ID, "email").send_keys(email_dizimista)
        driver.find_element(By.ID, "senha").send_keys("senha_valida123")
        _clicar_submit(driver)

        _aguardar_alerta_erro(driver)
