"""Testes E2E de CRUD e gestão de usuários."""

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from tests.selenium.helpers import (
    APP_BASE_URL,
    _aguardar_alerta_erro,
    _aguardar_carregamento_pagina,
    _aguardar_visivel,
    _cadastrar_administrador,
    _cadastrar_dizimista,
    _clicar_elemento,
    _criar_admin_logado,
    _email_unico,
    _linha_usuario,
    _selecionar_igreja,
    _selecionar_paroquia,
    _selecionar_perfil,
    _submeter_formulario,
)

pytestmark = pytest.mark.selenium


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
        from tests.selenium.helpers import _clicar_submit

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
        from tests.selenium.helpers import _clicar_submit

        _clicar_submit(driver)

        _aguardar_alerta_erro(driver)


def _preencher_campos_comuns(driver, nome: str, email: str, senha: str | None) -> None:
    """Forward para o helper do pacote, mantendo o arquivo autocontido."""
    from tests.selenium.helpers import _preencher_campos_comuns as helper

    helper(driver, nome, email, senha)
