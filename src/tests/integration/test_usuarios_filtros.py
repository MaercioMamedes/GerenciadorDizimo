"""Testes E2E (Selenium) do mecanismo de busca e filtro de usuários.

Cobrem a interação com o formulário de filtros, paginação e botão Limpar.
"""

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from app.models.perfil_dizimista import StatusCadastro
from app.models.usuario import PerfilUsuario

from .helpers import fazer_login, preencher_campo

# --------------------------------------------------------------------------- #
# URLs e seletores
# --------------------------------------------------------------------------- #
URL_LISTA_USUARIOS = "/usuarios"


def _abrir_lista(driver: WebDriver, base_url: str) -> None:
    driver.get(f"{base_url}{URL_LISTA_USUARIOS}")
    WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.TAG_NAME, "table"))
    )


def _contar_linhas_tabela(driver: WebDriver) -> int:
    return len(driver.find_elements(By.CSS_SELECTOR, "table tbody tr"))


def _obter_texto_linhas(driver: WebDriver) -> list[str]:
    linhas = driver.find_elements(By.CSS_SELECTOR, "table tbody tr td:first-child")
    return [c.text for c in linhas]


def _selecionar_opcao(driver: WebDriver, nome: str, valor: str) -> None:
    select = Select(driver.find_element(By.NAME, nome))
    select.select_by_value(valor)


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture
def admin_autenticado(driver: WebDriver, base_url: str, admin_criado):
    """Realiza login como administrador e retorna os dados do usuário."""
    fazer_login(
        driver, base_url, email=admin_criado["email"], senha=admin_criado["senha"]
    )
    return admin_criado


@pytest.fixture
async def usuarios_variados(db, paroquia_criada, igreja_criada):
    """Cria usuários diversos para validar os filtros na UI.

    Esta fixture depende das fixtures de banco existentes no projeto.
    """
    from app.models.perfil_dizimista import PerfilDizimista
    from app.models.usuario import Usuario

    admin = Usuario(
        nome="Selenium Admin",
        email="selenium.admin@example.com",
        perfil=PerfilUsuario.administrador,
        ativo=True,
        paroquia_id=paroquia_criada.id,
    )

    dizimista_ativo = Usuario(
        nome="Selenium Dizimista Ativo",
        email="selenium.dizimista@example.com",
        perfil=PerfilUsuario.dizimista,
        ativo=True,
        paroquia_id=paroquia_criada.id,
    )
    perfil = PerfilDizimista(
        usuario=dizimista_ativo,
        numero_registro=7777,
        status_cadastro=StatusCadastro.aprovado,
        igreja_id=igreja_criada.id,
    )

    db.add_all([admin, dizimista_ativo, perfil])
    await db.commit()

    return {"admin": admin, "dizimista": dizimista_ativo}


# --------------------------------------------------------------------------- #
# Testes de filtro por nome
# --------------------------------------------------------------------------- #
@pytest.mark.selenium
def test_filtro_por_nome_exibe_apenas_resultado_correspondente(
    driver: WebDriver, base_url: str, admin_autenticado, usuarios_variados
):
    _abrir_lista(driver, base_url)

    preencher_campo(driver, By.NAME, "busca", "Selenium Dizimista")
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    WebDriverWait(driver, 5).until(
        EC.text_to_be_present_in_element(
            (By.CSS_SELECTOR, "table tbody"), "Selenium Dizimista Ativo"
        )
    )

    nomes = _obter_texto_linhas(driver)
    assert nomes == ["Selenium Dizimista Ativo"]


@pytest.mark.selenium
def test_filtro_por_nome_inexistente_exibe_mensagem_vazia(
    driver: WebDriver, base_url: str, admin_autenticado, usuarios_variados
):
    _abrir_lista(driver, base_url)

    preencher_campo(driver, By.NAME, "busca", "NomeQueNaoExiste")
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    WebDriverWait(driver, 5).until(
        EC.text_to_be_present_in_element(
            (By.CSS_SELECTOR, "table tbody"), "Nenhum usuário encontrado"
        )
    )

    assert _contar_linhas_tabela(driver) == 1  # apenas a linha da mensagem vazia


# --------------------------------------------------------------------------- #
# Testes de filtro por número de registro
# --------------------------------------------------------------------------- #
@pytest.mark.selenium
def test_filtro_por_numero_registro(
    driver: WebDriver, base_url: str, admin_autenticado, usuarios_variados
):
    _abrir_lista(driver, base_url)

    preencher_campo(driver, By.NAME, "numero_registro", "7777")
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    WebDriverWait(driver, 5).until(
        EC.text_to_be_present_in_element(
            (By.CSS_SELECTOR, "table tbody"), "Selenium Dizimista Ativo"
        )
    )

    nomes = _obter_texto_linhas(driver)
    assert nomes == ["Selenium Dizimista Ativo"]


# --------------------------------------------------------------------------- #
# Testes de filtro por perfil
# --------------------------------------------------------------------------- #
@pytest.mark.selenium
def test_filtro_por_perfil_dizimista(
    driver: WebDriver, base_url: str, admin_autenticado, usuarios_variados
):
    _abrir_lista(driver, base_url)

    _selecionar_opcao(driver, "perfil", "dizimista")
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    WebDriverWait(driver, 5).until(
        EC.text_to_be_present_in_element(
            (By.CSS_SELECTOR, "table tbody"), "Selenium Dizimista Ativo"
        )
    )

    nomes = _obter_texto_linhas(driver)
    assert "Selenium Admin" not in nomes
    assert "Selenium Dizimista Ativo" in nomes


@pytest.mark.selenium
def test_filtro_por_perfil_administrador(
    driver: WebDriver, base_url: str, admin_autenticado, usuarios_variados
):
    _abrir_lista(driver, base_url)

    _selecionar_opcao(driver, "perfil", "administrador")
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    WebDriverWait(driver, 5).until(
        EC.text_to_be_present_in_element(
            (By.CSS_SELECTOR, "table tbody"), "Selenium Admin"
        )
    )

    nomes = _obter_texto_linhas(driver)
    assert "Selenium Admin" in nomes
    assert "Selenium Dizimista Ativo" not in nomes


# --------------------------------------------------------------------------- #
# Testes de filtro por situação
# --------------------------------------------------------------------------- #
@pytest.mark.selenium
def test_filtro_por_situacao_ativo(
    driver: WebDriver, base_url: str, admin_autenticado, usuarios_variados
):
    _abrir_lista(driver, base_url)

    _selecionar_opcao(driver, "ativo", "true")
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    WebDriverWait(driver, 5).until(
        EC.text_to_be_present_in_element(
            (By.CSS_SELECTOR, "table tbody"), "Selenium Dizimista Ativo"
        )
    )

    nomes = _obter_texto_linhas(driver)
    assert len(nomes) == 2
    assert all(n in nomes for n in ["Selenium Admin", "Selenium Dizimista Ativo"])


# --------------------------------------------------------------------------- #
# Testes de filtro por status de cadastro
# --------------------------------------------------------------------------- #
@pytest.mark.selenium
def test_filtro_por_status_cadastro_aprovado(
    driver: WebDriver, base_url: str, admin_autenticado, usuarios_variados
):
    _abrir_lista(driver, base_url)

    _selecionar_opcao(driver, "status_cadastro", "aprovado")
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    WebDriverWait(driver, 5).until(
        EC.text_to_be_present_in_element(
            (By.CSS_SELECTOR, "table tbody"), "Selenium Dizimista Ativo"
        )
    )

    nomes = _obter_texto_linhas(driver)
    assert nomes == ["Selenium Dizimista Ativo"]


# --------------------------------------------------------------------------- #
# Teste de paginação preservando filtros
# --------------------------------------------------------------------------- #
@pytest.mark.selenium
def test_paginacao_preserva_filtro_de_nome(
    driver: WebDriver, base_url: str, admin_autenticado, usuarios_variados
):
    _abrir_lista(driver, base_url)

    preencher_campo(driver, By.NAME, "busca", "Selenium")
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    WebDriverWait(driver, 5).until(
        EC.text_to_be_present_in_element(
            (By.CSS_SELECTOR, "table tbody"), "Selenium Admin"
        )
    )

    # Verifica que o filtro permanece no campo após o submit
    campo_busca = driver.find_element(By.NAME, "busca")
    assert campo_busca.get_attribute("value") == "Selenium"


# --------------------------------------------------------------------------- #
# Teste do botão Limpar
# --------------------------------------------------------------------------- #
@pytest.mark.selenium
def test_botao_limpar_reseta_filtros(
    driver: WebDriver, base_url: str, admin_autenticado, usuarios_variados
):
    _abrir_lista(driver, base_url)

    preencher_campo(driver, By.NAME, "busca", "Selenium Dizimista")
    _selecionar_opcao(driver, "perfil", "dizimista")
    _selecionar_opcao(driver, "ativo", "true")
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    WebDriverWait(driver, 5).until(
        EC.text_to_be_present_in_element(
            (By.CSS_SELECTOR, "table tbody"), "Selenium Dizimista Ativo"
        )
    )

    driver.find_element(By.LINK_TEXT, "Limpar").click()

    WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.TAG_NAME, "table"))
    )

    # Filtros devem estar reiniciados
    assert driver.find_element(By.NAME, "busca").get_attribute("value") == ""
    perfil = Select(driver.find_element(By.NAME, "perfil")).first_selected_option.text
    assert perfil == "Todos"
    ativo = Select(driver.find_element(By.NAME, "ativo")).first_selected_option.text
    assert ativo == "Todos"

    # Resultado deve conter todos os usuários criados
    nomes = _obter_texto_linhas(driver)
    assert "Selenium Admin" in nomes
    assert "Selenium Dizimista Ativo" in nomes
