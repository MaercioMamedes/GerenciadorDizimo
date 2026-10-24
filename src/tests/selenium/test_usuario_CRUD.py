"""Testes E2E de CRUD e gestão de usuários."""

import asyncio
import re
from datetime import datetime

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
    _clicar_submit,
    _criar_admin_logado,
    _email_unico,
    _linha_usuario,
    _login,
    _selecionar_igreja,
    _selecionar_paroquia,
    _selecionar_perfil,
    _submeter_formulario,
)

pytestmark = pytest.mark.selenium


def _preencher_campos_comuns(driver, nome: str, email: str | None, senha: str | None) -> None:
    """Forward para o helper do pacote, mantendo o arquivo autocontido."""
    from tests.selenium.helpers import _preencher_campos_comuns as helper
    helper(driver, nome, email or "", senha or "")


def _extrair_data_hora(driver, rotulo: str) -> str:
    """Extrai o valor renderizado ao lado de um rótulo na página de detalhes."""
    elemento = driver.find_element(
        By.XPATH,
        f"//dt[contains(text(), '{rotulo}')]/following-sibling::dd[1]",
    )
    return elemento.text.strip()


def _formato_data_hora_valido(valor: str) -> bool:
    """Valida formato 'dd/mm/aaaa hh:mm' esperado no timezone local."""
    return bool(re.fullmatch(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}", valor))


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

        _submeter_formulario(driver, forcar=True, esperar_redirecionamento=False)
        _aguardar_alerta_erro(driver)

    async def test_cadastro_publico_sem_igreja_nao_envia(self, driver):
        driver.get(f"{APP_BASE_URL}/usuarios/novo")
        _aguardar_carregamento_pagina(driver)

        _preencher_campos_comuns(
            driver, "Sem Igreja", _email_unico(), "senha_valida123"
        )

        _submeter_formulario(driver, forcar=True, esperar_redirecionamento=False)

        _aguardar_alerta_erro(driver)
        alerta = driver.find_element(By.CSS_SELECTOR, ".alert-danger")
        assert "igreja" in alerta.text.lower()

    # -----------------------------------------------------------------------
    # Novos testes Selenium: campo e geração de número de registro
    # -----------------------------------------------------------------------

    async def test_autocadastro_nao_exibe_campo_numero_registro(self, driver):
        """Campo número de registro não deve existir no autocadastro público."""
        driver.get(f"{APP_BASE_URL}/usuarios/novo")
        _aguardar_carregamento_pagina(driver)

        assert len(driver.find_elements(By.ID, "numero_registro")) == 0

    async def test_autocadastro_nao_gera_numero_registro(self, driver):
        """Autocadastro válido deve criar dizimista sem número de registro."""
        email = _email_unico()
        _cadastrar_dizimista(driver, "Dizimista Sem Registro", email, "senha_valida123")

        # Admin verifica o cadastro recém-criado
        await _criar_admin_logado(driver)

        driver.get(f"{APP_BASE_URL}/usuarios?tamanho_pagina=100")
        linha = _linha_usuario(driver, "Dizimista Sem Registro")
        _clicar_elemento(driver, linha.find_element(By.LINK_TEXT, "Detalhes"))

        WebDriverWait(driver, 8).until(EC.url_contains("/usuarios/"))
        assert "Número de registro" in driver.page_source
        assert "—" in driver.page_source


class TestCadastroPorAdministrador:
    async def test_admin_cria_dizimista_sem_email_sem_senha(self, driver):
        """CASO 1: admin cadastra dizimista sem e-mail, sem senha e sem número de registro."""
        await _criar_admin_logado(driver)

        driver.get(f"{APP_BASE_URL}/usuarios/novo")
        _aguardar_carregamento_pagina(driver)

        driver.find_element(By.ID, "nome").send_keys("Dizimista Sem Email")
        # Não preenche e-mail, senha, confirmar_senha nem numero_registro
        _selecionar_igreja(driver)
        _clicar_submit(driver)

        WebDriverWait(driver, 8).until(EC.url_to_be(f"{APP_BASE_URL}/usuarios"))

        driver.get(f"{APP_BASE_URL}/usuarios?tamanho_pagina=100")
        linha = _linha_usuario(driver, "Dizimista Sem Email")
        _clicar_elemento(driver, linha.find_element(By.LINK_TEXT, "Detalhes"))

        WebDriverWait(driver, 8).until(EC.url_contains("/usuarios/"))
        assert "Dizimista Sem Email" in driver.page_source
        assert "Número de registro" in driver.page_source
        assert "—" in driver.page_source


    async def test_admin_cria_dizimista_com_numero_registro(self, driver):
        await _criar_admin_logado(driver)

        driver.get(f"{APP_BASE_URL}/usuarios/novo")
        _aguardar_carregamento_pagina(driver)

        driver.find_element(By.ID, "nome").send_keys("Dizimista Com Registro")
        driver.find_element(By.ID, "numero_registro").send_keys("1001")
        _selecionar_igreja(driver)
        _clicar_submit(driver)

        WebDriverWait(driver, 8).until(EC.url_to_be(f"{APP_BASE_URL}/usuarios"))

        driver.get(f"{APP_BASE_URL}/usuarios?tamanho_pagina=100")
        linha = _linha_usuario(driver, "Dizimista Com Registro")
        _clicar_elemento(driver, linha.find_element(By.LINK_TEXT, "Detalhes"))

        WebDriverWait(driver, 8).until(EC.url_contains("/usuarios/"))
        assert "1001" in driver.page_source

    async def test_numero_registro_duplicado_mostra_erro(self, driver):
        await _criar_admin_logado(driver)

        driver.get(f"{APP_BASE_URL}/usuarios/novo")
        _aguardar_carregamento_pagina(driver)

        driver.find_element(By.ID, "nome").send_keys("Primeiro Com Registro")
        driver.find_element(By.ID, "numero_registro").send_keys("2002")
        _selecionar_igreja(driver)
        _clicar_submit(driver)
        WebDriverWait(driver, 8).until(EC.url_to_be(f"{APP_BASE_URL}/usuarios"))

        driver.get(f"{APP_BASE_URL}/usuarios/novo")
        _aguardar_carregamento_pagina(driver)

        driver.find_element(By.ID, "nome").send_keys("Segundo Com Registro")
        driver.find_element(By.ID, "numero_registro").send_keys("2002")
        _selecionar_igreja(driver)
        _submeter_formulario(driver, forcar=True, esperar_redirecionamento=False)

        _aguardar_alerta_erro(driver)
        alerta = driver.find_element(By.CSS_SELECTOR, ".alert-danger")
        assert "número de registro" in alerta.text.lower()

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

        driver.get(f"{APP_BASE_URL}/usuarios?tamanho_pagina=100")
        assert email in driver.page_source

    async def test_admin_cria_administrador_sem_paroquia_mostra_erro(self, driver):
        await _criar_admin_logado(driver)

        email = _email_unico()
        driver.get(f"{APP_BASE_URL}/usuarios/novo")
        _aguardar_carregamento_pagina(driver)

        _preencher_campos_comuns(driver, "Admin Sem Paróquia", email, "senha_valida123")
        _selecionar_perfil(driver, "administrador")

        _aguardar_visivel(driver, By.ID, "campo-paroquia")

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

    # -----------------------------------------------------------------------
    # Novo teste Selenium: campo visível apenas para admin
    # -----------------------------------------------------------------------

    async def test_admin_ve_campo_numero_registro_no_formulario(self, driver):
        """Administrador logado deve ver o campo número de registro no formulário."""
        await _criar_admin_logado(driver)

        driver.get(f"{APP_BASE_URL}/usuarios/novo")
        _aguardar_carregamento_pagina(driver)

        campo = driver.find_element(By.ID, "numero_registro")
        assert campo.is_displayed()


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

        _selecionar_paroquia(driver)

        _aguardar_visivel(driver, By.ID, "tambem_dizimista")
        checkbox = driver.find_element(By.ID, "tambem_dizimista")
        _clicar_elemento(driver, checkbox)

        _aguardar_visivel(driver, By.ID, "campos-dizimista")
        _selecionar_igreja(driver)

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


class TestTimestampsUsuario:
    async def test_timestamps_aparecem_apos_criacao(self, driver):
        """Após criar um usuário, os metadados de tempo devem ser exibidos no template."""
        await _criar_admin_logado(driver)

        email = _email_unico()
        _cadastrar_dizimista(driver, "Timestamp Criacao", email, "senha_valida123")

        driver.get(f"{APP_BASE_URL}/usuarios?tamanho_pagina=100")
        linha = _linha_usuario(driver, "Timestamp Criacao")
        _clicar_elemento(driver, linha.find_element(By.LINK_TEXT, "Detalhes"))

        WebDriverWait(driver, 8).until(EC.url_contains("/usuarios/"))

        criado_em = _extrair_data_hora(driver, "Criado em")
        atualizado_em = _extrair_data_hora(driver, "Atualizado em")

        assert criado_em != "—"
        assert atualizado_em != "—"
        assert _formato_data_hora_valido(criado_em)
        assert _formato_data_hora_valido(atualizado_em)

    async def test_atualizado_em_muda_apos_edicao(self, driver):
        """Após editar um usuário, atualizado_em deve mudar no template; criado_em não."""
        await _criar_admin_logado(driver)

        email = _email_unico()
        _cadastrar_dizimista(driver, "Timestamp Edicao", email, "senha_valida123")

        driver.get(f"{APP_BASE_URL}/usuarios?tamanho_pagina=100")
        linha = _linha_usuario(driver, "Timestamp Edicao")
        _clicar_elemento(driver, linha.find_element(By.LINK_TEXT, "Detalhes"))

        WebDriverWait(driver, 8).until(EC.url_contains("/usuarios/"))

        criado_em_antes = _extrair_data_hora(driver, "Criado em")
        atualizado_em_antes = _extrair_data_hora(driver, "Atualizado em")

        # Aguarda o próximo minuto para que o template exiba valor diferente
        agora = datetime.now()
        segundos_ate_proximo_minuto = 60 - agora.second
        await asyncio.sleep(segundos_ate_proximo_minuto + 1)

        driver.get(f"{APP_BASE_URL}/usuarios?tamanho_pagina=100")
        linha = _linha_usuario(driver, "Timestamp Edicao")
        _clicar_elemento(driver, linha.find_element(By.LINK_TEXT, "Editar"))

        WebDriverWait(driver, 8).until(EC.url_contains("/editar"))
        _aguardar_visivel(driver, By.ID, "nome")

        campo_nome = driver.find_element(By.ID, "nome")
        campo_nome.clear()
        campo_nome.send_keys("Timestamp Edicao Atualizado")

        _submeter_formulario(driver)

        WebDriverWait(driver, 8).until(EC.url_to_be(f"{APP_BASE_URL}/usuarios"))

        driver.get(f"{APP_BASE_URL}/usuarios?tamanho_pagina=100")
        linha = _linha_usuario(driver, "Timestamp Edicao Atualizado")
        _clicar_elemento(driver, linha.find_element(By.LINK_TEXT, "Detalhes"))

        WebDriverWait(driver, 8).until(EC.url_contains("/usuarios/"))

        criado_em_depois = _extrair_data_hora(driver, "Criado em")
        atualizado_em_depois = _extrair_data_hora(driver, "Atualizado em")

        assert criado_em_antes == criado_em_depois
        assert atualizado_em_antes != atualizado_em_depois
        assert _formato_data_hora_valido(atualizado_em_depois)

    async def test_atualizado_em_muda_apos_edicao_apenas_perfil_dizimista(self, driver):
        """Alterar apenas um campo do PerfilDizimista deve atualizar o timestamp de Usuário."""
        await _criar_admin_logado(driver)

        driver.get(f"{APP_BASE_URL}/usuarios/novo")
        _aguardar_carregamento_pagina(driver)

        driver.find_element(By.ID, "nome").send_keys("Timestamp Perfil Dizimista")
        driver.find_element(By.ID, "numero_registro").send_keys("3003")
        _selecionar_igreja(driver)
        _clicar_submit(driver)

        WebDriverWait(driver, 8).until(EC.url_to_be(f"{APP_BASE_URL}/usuarios"))

        driver.get(f"{APP_BASE_URL}/usuarios?tamanho_pagina=100")
        linha = _linha_usuario(driver, "Timestamp Perfil Dizimista")
        _clicar_elemento(driver, linha.find_element(By.LINK_TEXT, "Detalhes"))

        WebDriverWait(driver, 8).until(EC.url_contains("/usuarios/"))

        criado_em_antes = _extrair_data_hora(driver, "Criado em")
        atualizado_em_antes = _extrair_data_hora(driver, "Atualizado em")

        assert "3003" in driver.page_source

        # Aguarda o próximo minuto, já que o template exibe hh:mm sem segundos
        agora = datetime.now()
        segundos_ate_proximo_minuto = 60 - agora.second
        await asyncio.sleep(segundos_ate_proximo_minuto + 1)

        driver.get(f"{APP_BASE_URL}/usuarios?tamanho_pagina=100")
        linha = _linha_usuario(driver, "Timestamp Perfil Dizimista")
        _clicar_elemento(driver, linha.find_element(By.LINK_TEXT, "Editar"))

        WebDriverWait(driver, 8).until(EC.url_contains("/editar"))
        _aguardar_visivel(driver, By.ID, "numero_registro")

        campo_numero = driver.find_element(By.ID, "numero_registro")
        campo_numero.clear()
        campo_numero.send_keys("3004")

        _submeter_formulario(driver)

        WebDriverWait(driver, 8).until(EC.url_to_be(f"{APP_BASE_URL}/usuarios"))

        driver.get(f"{APP_BASE_URL}/usuarios?tamanho_pagina=100")
        linha = _linha_usuario(driver, "Timestamp Perfil Dizimista")
        _clicar_elemento(driver, linha.find_element(By.LINK_TEXT, "Detalhes"))

        WebDriverWait(driver, 8).until(EC.url_contains("/usuarios/"))

        criado_em_depois = _extrair_data_hora(driver, "Criado em")
        atualizado_em_depois = _extrair_data_hora(driver, "Atualizado em")

        assert "3004" in driver.page_source
        assert criado_em_antes == criado_em_depois
        assert atualizado_em_antes != atualizado_em_depois
        assert _formato_data_hora_valido(atualizado_em_depois)


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
