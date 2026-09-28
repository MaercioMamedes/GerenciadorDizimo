import uuid

import pytest
from fastapi import HTTPException

from app.api.v1.deps import require_perfil
from app.models.usuario import PerfilUsuario, Usuario


def _usuario(perfil: PerfilUsuario) -> Usuario:
    return Usuario(
        id=uuid.uuid4(),
        nome="Teste",
        email="teste@teste.com",
        senha_hash="hash",
        perfil=perfil,
        ativo=True,
    )


def test_require_perfil_permite_acesso():
    verificador = require_perfil(PerfilUsuario.ADMINISTRADOR)
    usuario = _usuario(PerfilUsuario.ADMINISTRADOR)

    resultado = verificador(usuario=usuario)

    assert resultado is usuario


def test_require_perfil_nega_acesso():
    verificador = require_perfil(PerfilUsuario.ADMINISTRADOR)
    usuario = _usuario(PerfilUsuario.DIZIMISTA)

    with pytest.raises(HTTPException) as exc:
        verificador(usuario=usuario)

    assert exc.value.status_code == 403
    assert "permissão" in exc.value.detail.lower()


def test_require_perfil_multiplos_perfis():
    verificador = require_perfil(PerfilUsuario.ADMINISTRADOR, PerfilUsuario.DIZIMISTA)
    usuario = _usuario(PerfilUsuario.DIZIMISTA)

    resultado = verificador(usuario=usuario)

    assert resultado is usuario
