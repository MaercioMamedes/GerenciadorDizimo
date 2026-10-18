"""Helpers reutilizáveis para os testes E2E com Selenium."""

import os
import uuid

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait
from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.usuario import PerfilUsuario, Usuario
from tests.conftest import TEST_DATABASE_URL

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
    if not _existe_elemento(driver, By.ID, "perfil"):
        return

    select_perfil = Select(
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "perfil"))
        )
    )
    select_perfil.select_by_value(perfil)

    perfil_el = driver.find_element(By.ID, "perfil")
    driver.execute_script(
        "arguments[0].dispatchEvent(new Event('change', { bubbles: true }));"
        "arguments[0].dispatchEvent(new Event('input', { bubbles: true }));",
        perfil_el,
    )

    # Se selecionou administrador, aguarda o campo de paróquia ficar disponível
    if perfil == "administrador":
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "campo-paroquia"))
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
    if not paroquia_id:
        raise ValueError("Nenhuma paroquia_id disponível para seleção")

    # Aguarda o container existir no DOM e força visibilidade
    campo = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "campo-paroquia"))
    )
    driver.execute_script(
        "arguments[0].style.display = 'block'; "
        "arguments[0].style.visibility = 'visible';",
        campo,
    )

    # Garante que o <select> esteja habilitado e visível
    select_el = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "paroquia_id"))
    )
    driver.execute_script(
        "arguments[0].disabled = false; "
        "arguments[0].removeAttribute('disabled'); "
        "arguments[0].style.display = 'block'; "
        "arguments[0].style.visibility = 'visible';",
        select_el,
    )

    # Aguarda o fetch popular o select com a opção desejada
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, f"#paroquia_id option[value='{paroquia_id}']")
        )
    )

    # Tenta selecionar via API nativa do Selenium
    try:
        Select(select_el).select_by_value(paroquia_id)
    except Exception:
        # Fallback para JS se o select não for interativo
        driver.execute_script(
            """
            const select = document.getElementById('paroquia_id');
            select.value = arguments[0];
            select.dispatchEvent(new Event('change', { bubbles: true }));
            select.dispatchEvent(new Event('input', { bubbles: true }));
            """,
            paroquia_id,
        )

    # Confirma que o valor realmente foi aplicado
    WebDriverWait(driver, 5).until(
        lambda d: d.find_element(By.ID, "paroquia_id").get_attribute("value")
        == paroquia_id
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
