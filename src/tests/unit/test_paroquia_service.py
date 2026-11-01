import pytest

from app.schemas.paroquia import ParoquiaCreate, ParoquiaUpdate
from app.services import paroquia_service
from app.services.paroquia_service import ParoquiaNaoEncontrada

pytestmark = pytest.mark.asyncio


async def test_criar_paroquia(db_session):
    dados = ParoquiaCreate(
        nome_matriz="Paróquia São Francisco",
        cnpj="12.345.678/0001-90",
        endereco_matriz="Rua das Flores, 100",
    )
    paroquia = await paroquia_service.criar_paroquia(db_session, dados)

    assert paroquia.id is not None
    assert paroquia.nome == "Paróquia São Francisco"


async def test_listar_paroquias(db_session):
    await paroquia_service.criar_paroquia(
        db_session,
        ParoquiaCreate(
            nome_matriz="Paróquia A", cnpj=None, endereco_matriz="Endereço A"
        ),
    )
    await paroquia_service.criar_paroquia(
        db_session,
        ParoquiaCreate(
            nome_matriz="Paróquia B", cnpj=None, endereco_matriz="Endereço B"
        ),
    )

    resultado = await paroquia_service.listar_paroquias(db_session)
    assert len(resultado) == 2


async def test_obter_paroquia_inexistente_lanca_erro(db_session):
    import uuid

    with pytest.raises(ParoquiaNaoEncontrada):
        await paroquia_service.obter_paroquia(db_session, uuid.uuid4())


async def test_atualizar_paroquia(db_session):
    paroquia = await paroquia_service.criar_paroquia(
        db_session,
        ParoquiaCreate(
            nome_matriz="Nome Antigo", cnpj=None, endereco_matriz="Endereço Antigo"
        ),
    )

    dados_atualizados = ParoquiaUpdate(cnpj="98.765.432/0001-10")
    atualizada = await paroquia_service.atualizar_paroquia(
        db_session, paroquia.id, dados_atualizados
    )

    assert atualizada.cnpj == "98.765.432/0001-10"
