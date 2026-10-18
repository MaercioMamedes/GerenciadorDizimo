"""Testes E2E de autenticação e autorização (login, logout, sessão)."""

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from tests.selenium.helpers import (
    APP_BASE_URL,
    _aguardar_alerta_erro,
    _aguardar_carregamento_pagina,
    _aprovar_dizimista,
    _cadastrar_dizimista,
    _clicar_elemento,
    _clicar_submit,
    _criar_admin_logado,
    _email_unico,
    _login,
)

pytestmark = pytest.mark.selenium


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


class TestAcessoRestrito:
    async def test_usuario_nao_logado_e_redirecionado_para_login(self, driver):
        driver.get(f"{APP_BASE_URL}/usuarios")
        WebDriverWait(driver, 8).until(EC.url_contains("/auth/login"))

    async def test_dizimista_nao_acessa_lista_de_usuarios(self, driver):
        email = _email_unico()
        senha = "senha_valida123"
        _cadastrar_dizimista(driver, "Dizimista Restrito", email, senha)
        await _aprovar_dizimista(email)
        _login(driver, email, senha)

        driver.get(f"{APP_BASE_URL}/usuarios")
        _aguardar_carregamento_pagina(driver)

        # A aplicação pode redirecionar ou bloquear na própria página.
        # Qualquer uma dessas respostas é aceitável desde que o dizimista
        # não veja a lista administrativa de usuários.
        if driver.current_url == f"{APP_BASE_URL}/usuarios":
            assert (
                "não autorizado" in driver.page_source.lower()
                or "acesso negado" in driver.page_source.lower()
                or len(driver.find_elements(By.CSS_SELECTOR, "table")) == 0
            )
        else:
            assert driver.current_url in [
                f"{APP_BASE_URL}/",
                f"{APP_BASE_URL}/auth/login",
            ]

    async def test_admin_acessa_lista_de_usuarios(self, driver):
        await _criar_admin_logado(driver)

        driver.get(f"{APP_BASE_URL}/usuarios?tamanho_pagina=100")
        _aguardar_carregamento_pagina(driver)

        WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table"))
        )

