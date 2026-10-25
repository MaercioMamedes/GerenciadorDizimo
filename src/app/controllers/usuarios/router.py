"""Roteamento do módulo de usuários.

Reexporta os handlers com o prefixo /usuarios.
A ordem de registro importa: rotas estáticas primeiro, dinâmicas depois.
"""

from fastapi import APIRouter

from app.controllers.usuarios.cadastro import (
    cadastrar_usuario_via_formulario,
    formulario_cadastro_usuario,
)
from app.controllers.usuarios.edicao import editar_usuario_via_formulario
from app.controllers.usuarios.exclusao import excluir_usuario_via_formulario
from app.controllers.usuarios.listagem import (
    detalhes_usuario_view,
    listar_usuarios_view,
)

router = APIRouter(prefix="/usuarios", tags=["Controllers - Usuários"])

router.get("/novo")(formulario_cadastro_usuario)
router.post("/novo")(cadastrar_usuario_via_formulario)

router.get("")(listar_usuarios_view)

router.get("/{usuario_id}")(detalhes_usuario_view)
router.get("/{usuario_id}/editar")(editar_usuario_via_formulario)
router.post("/{usuario_id}/editar")(editar_usuario_via_formulario)
router.post("/{usuario_id}/excluir")(excluir_usuario_via_formulario)
