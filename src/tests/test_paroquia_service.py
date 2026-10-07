import pytest

from app.schemas.paroquia import ParoquiaCreate, ParoquiaUpdate
from app.services import paroquia_service
from app.services.paroquia_service import ParoquiaNaoEncontrada

pytestmark = pytest.mark.asyncio


async def test_criar_paroquia(db_session):
    dados = ParoquiaCreate(nome="Paróquia São Francisco", cnpj="12.345.678/0001-90",
                            endereco="Rua das Flores, 100")
    paroquia = await paroquia_service.criar_paroquia(db_session, dados)

    assert paroquia.id is not None
    assert paroquia.nome == "Paróquia São Francisco"


async def test_listar_paroquias(db_session):
    await paroquia_service.criar_paroquia(
        db_session, ParoquiaCreate(nome="Paróquia A", cnpj=None, endereco=None)
    )
    await paroquia_service.criar_paroquia(
        db_session, ParoquiaCreate(nome="Paróquia B", cnpj=None, endereco=None)
    )

    resultado = await paroquia_service.listar_paroquias(db_session)
    assert len(resultado) == 2


async def test_obter_paroquia_inexistente_lanca_erro(db_session):
    import uuid

    with pytest.raises(ParoquiaNaoEncontrada):
        await paroquia_service.obter_paroquia(db_session, uuid.uuid4())


async def test_atualizar_paroquia(db_session):
    paroquia = await paroquia_service.criar_paroquia(
        db_session, ParoquiaCreate(nome="Nome Antigo", cnpj=None, endereco=None)
    )

    dados_atualizados = ParoquiaUpdate(nome="Nome Novo", cnpj=None, endereco=None)
    atualizada = await paroquia_service.atualizar_paroquia(
        db_session, paroquia.id, dados_atualizados
    )

    assert atualizada.nome == "Nome Novo"
