"""Testes unitários das funções auxiliares do controller de listagem.

Validam a normalização de texto e a conversão segura de booleanos e datas
recebidas como query parameters da interface.
"""

import pytest

from app.controllers.usuarios.listagem import (
    _converter_ativo,
    _converter_data,
    _normalizar_texto,
)


def test_normalizar_texto_remove_espacos_e_vazio():
    assert _normalizar_texto("  administrador  ") == "administrador"


def test_normalizar_texto_vazio_retorna_none():
    assert _normalizar_texto("") is None
    assert _normalizar_texto("   ") is None


def test_normalizar_texto_none_retorna_none():
    assert _normalizar_texto(None) is None


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("true", True),
        ("True", True),
        ("TRUE", True),
        ("1", True),
        ("on", True),
        ("yes", True),
        ("false", False),
        ("False", False),
        ("FALSE", False),
        ("0", False),
        ("off", False),
        ("no", False),
        ("", None),
        ("   ", None),
        (None, None),
    ],
)
def test_converter_ativo(entrada, esperado):
    assert _converter_ativo(entrada) == esperado


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("2026-10-25", __import__("datetime").date(2026, 10, 25)),
        ("", None),
        ("   ", None),
        (None, None),
        ("data-invalida", None),
        ("25/10/2026", None),  # formato brasileiro não aceito
    ],
)
def test_converter_data(entrada, esperado):
    assert _converter_data(entrada) == esperado
