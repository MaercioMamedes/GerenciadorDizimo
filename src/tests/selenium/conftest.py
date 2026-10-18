"""Fixtures compartilhadas para os testes E2E com Selenium."""

import asyncio

import pytest
import pytest_asyncio
from selenium.webdriver.remote.client_config import ClientConfig
from sqlalchemy import select, text

from app.models.igreja import Igreja
from app.models.paroquia import Paroquia
from selenium import webdriver
from tests.conftest import _ensure_test_database_exists, _run_alembic_upgrade
from tests.selenium import helpers


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _garantir_banco_de_teste_migrado():
    await _ensure_test_database_exists()

    sync_test_url = helpers.TEST_DATABASE_URL.replace("+asyncpg", "")
    await asyncio.to_thread(_run_alembic_upgrade, sync_test_url)

    async with helpers._async_session_maker() as session:
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

        helpers._PAROQUIA_ID = str(paroquia.id)
        helpers._IGREJA_ID = str(igreja.id)

    yield

    async with helpers._engine_test.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE TABLE "
                "usuario, igreja, paroquia, perfil_dizimista, "
                "contribuicao, consentimento_lgpd, security_log, audit_log "
                "RESTART IDENTITY CASCADE"
            )
        )

    await helpers._engine_test.dispose()




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
        f"{helpers.APP_BASE_URL},http://app:8000,http://app.local:8000"
    )
    options.set_capability("acceptInsecureCerts", True)

    client_config = ClientConfig(
        remote_server_addr=helpers.SELENIUM_REMOTE_URL,
        timeout=20,
    )

    navegador = webdriver.Remote(
        command_executor=helpers.SELENIUM_REMOTE_URL,
        options=options,
        client_config=client_config,
    )
    navegador.set_page_load_timeout(15)
    navegador.implicitly_wait(2)
    navegador.set_window_size(1920, 1080)
    yield navegador
    navegador.quit()
