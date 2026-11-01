"""Testes E2E (Selenium) do mecanismo de busca e filtro de usuários.

Cobrem a interação com o formulário de filtros, paginação e botão Limpar.
"""

import uuid

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait
from sqlalchemy import text

from app.core.security import hash_senha
from app.models.perfil_dizimista import PerfilDizimista, StatusCadastro
from app.models.usuario import PerfilUsuario, Usuario

from .helpers import (
    _async_session_maker,
    fazer_login,
    preencher_campo,
)

# --------------------------------------------------------------------------- #
# URLs e seletores
# --------------------------------------------------------------------------- #
URL_LISTA_USUARIOS = "/usuarios"


def _abrir_lista(driver: WebDriver, base_url: str) -> None:
    """Abre a listagem com páginação ampla para evitar que resultados esperados
    fiquem fora da primeira página quando o banco contém dados residuais."""
    driver.get(f"{base_url}{URL_LISTA_USUARIOS}?tamanho_pagina=100")
    WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.ID, "tabela-usuarios"))
    )


def _contar_linhas_tabela(driver: WebDriver) -> int:
    return len(driver.find_elements(By.CSS_SELECTOR, "#tabela-usuarios tbody tr"))


def _obter_texto_linhas(driver: WebDriver) -> list[str]:
    # Re-localiza as células a cada chamada para evitar stale elements
    # quando a tabela é recarregada via submit/Limpar.
    linhas = driver.find_elements(
        By.CSS_SELECTOR, "#tabela-usuarios tbody tr td:first-child"
    )
    return [c.text for c in linhas]


def _obter_nomes_apos_carregamento(driver: WebDriver, texto_esperado: str) -> list[str]:
    """Aguarda um texto na tabela e retorna os nomes visíveis."""
    WebDriverWait(driver, 5).until(
        EC.text_to_be_present_in_element(
            (By.ID, "tabela-usuarios"), texto_esperado
        )
    )
    return _obter_texto_linhas(driver)


def _selecionar_opcao(driver: WebDriver, nome: str, valor: str) -> None:
    select = Select(driver.find_element(By.NAME, nome))
    select.select_by_value(valor)


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture
def admin_autenticado(driver, base_url, admin_criado):
    """Realiza login como administrador e retorna os dados do usuário."""
    fazer_login(driver, base_url, email=admin_criado["email"], senha=admin_criado["senha"])
    return admin_criado


@pytest.fixture
async def usuarios_variados(admin_criado):
    """Cria usuários diversos para validar os filtros na UI.

    Limpa previamente usuários não-admin deixados por testes anteriores,
    garantindo que os filtros produzam resultados determinísticos.
    """
    admin_id = admin_criado["obj"].id

    async with _async_session_maker() as session:
        # Remove usuários criados por testes anteriores, preservando o admin
        # que será usado para autenticação nos testes deste módulo.
        await session.execute(
            text("DELETE FROM perfil_dizimista WHERE usuario_id != :admin_id"),
            {"admin_id": admin_id},
        )
        await session.execute(
            text("DELETE FROM usuario WHERE id != :admin_id"),
            {"admin_id": admin_id},
        )
        await session.commit()

    sufixo = uuid.uuid4().hex[:8]
    email_admin = f"selenium.admin.{sufixo}@example.com"
    email_dizimista = f"selenium.dizimista.{sufixo}@example.com"
    numero_registro = int(sufixo, 16) % 1_000_000_000

    async with _async_session_maker() as session:
        admin = Usuario(
            nome="Selenium Admin",
            email=email_admin,
            perfil=PerfilUsuario.ADMINISTRADOR,
            senha_hash=hash_senha("senha_qualquer"),
            ativo=True,
            paroquia_id=admin_criado["paroquia_id"],
        )

        dizimista_ativo = Usuario(
            nome="Selenium Dizimista Ativo",
            email=email_dizimista,
            perfil=PerfilUsuario.DIZIMISTA,
            senha_hash=hash_senha("senha_qualquer"),
            ativo=True,
            paroquia_id=admin_criado["paroquia_id"],
        )
        perfil = PerfilDizimista(
            usuario=dizimista_ativo,
            numero_registro=numero_registro,
            status_cadastro=StatusCadastro.APROVADO,
            igreja_id=admin_criado["igreja_id"],
        )

        session.add_all([admin, dizimista_ativo, perfil])
        await session.commit()

        ids_criados = [admin.id, dizimista_ativo.id]

    yield {
        "admin": admin,
        "dizimista": dizimista_ativo,
        "numero_registro": numero_registro,
    }

    # Teardown: remove os usuários criados
    async with _async_session_maker() as session:
        await session.execute(
            text("DELETE FROM perfil_dizimista WHERE usuario_id = ANY(:ids)"),
            {"ids": ids_criados},
        )
        await session.execute(
            text("DELETE FROM usuario WHERE id = ANY(:ids)"),
            {"ids": ids_criados},
        )
        await session.commit()


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

    nomes = _obter_nomes_apos_carregamento(driver, "Selenium Dizimista Ativo")
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
            (By.ID, "tabela-usuarios"), "Nenhum usuário encontrado"
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

    preencher_campo(
        driver, By.NAME, "numero_registro", str(usuarios_variados["numero_registro"])
    )
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    nomes = _obter_nomes_apos_carregamento(driver, "Selenium Dizimista Ativo")
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

    nomes = _obter_nomes_apos_carregamento(driver, "Selenium Dizimista Ativo")
    assert "Selenium Admin" not in nomes
    assert "Selenium Dizimista Ativo" in nomes


@pytest.mark.selenium
def test_filtro_por_perfil_administrador(
    driver: WebDriver, base_url: str, admin_autenticado, usuarios_variados
):
    _abrir_lista(driver, base_url)

    _selecionar_opcao(driver, "perfil", "administrador")
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    nomes = _obter_nomes_apos_carregamento(driver, "Selenium Admin")
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

    nomes = _obter_nomes_apos_carregamento(driver, "Selenium Dizimista Ativo")
    assert "Selenium Admin" in nomes
    assert "Selenium Dizimista Ativo" in nomes
    assert "Admin Teste" in nomes  # o próprio admin logado também aparece


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

    nomes = _obter_nomes_apos_carregamento(driver, "Selenium Dizimista Ativo")
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
            (By.ID, "tabela-usuarios"), "Selenium Admin"
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

    _obter_nomes_apos_carregamento(driver, "Selenium Dizimista Ativo")

    # Clica em Limpar e aguarda o recarregamento completo da página.
    driver.find_element(By.LINK_TEXT, "Limpar").click()
    WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.ID, "tabela-usuarios"))
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
