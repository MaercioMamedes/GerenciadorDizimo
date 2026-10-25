"""Handlers de edição de usuários."""

import uuid

from fastapi import Depends, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.controllers.deps import require_admin_view
from app.controllers.usuarios.context import (
    carregar_igrejas,
    carregar_paroquias,
    renderizar_formulario_usuario,
)
from app.controllers.usuarios.forms import parse_formulario_edicao
from app.controllers.usuarios.helpers import (
    buscar_usuario_com_relacionamentos,
    montar_payload_perfil_dizimista,
    perfil_e_dizimista,
)
from app.controllers.usuarios.validators import validar_formulario_edicao
from app.db.session import get_db
from app.models.usuario import PerfilUsuario
from app.schemas.usuario import UsuarioUpdate
from app.services.usuario_service import atualizar_usuario, remover_perfil_dizimista


async def formulario_editar_usuario(
    request: Request,
    usuario_id: uuid.UUID,
    usuario_atual=Depends(require_admin_view),
    db: AsyncSession = Depends(get_db),
):
    usuario = await buscar_usuario_com_relacionamentos(db, usuario_id)
    paroquias = await carregar_paroquias(db)
    igrejas = await carregar_igrejas(db)

    return renderizar_formulario_usuario(
        request=request,
        usuario_atual=usuario_atual,
        usuario=usuario,
        erros=[],
        paroquias=paroquias,
        igrejas=igrejas,
    )


async def editar_usuario_via_formulario(
    request: Request,
    usuario_id: uuid.UUID,
    usuario_atual=Depends(require_admin_view),
    db: AsyncSession = Depends(get_db),
):
    usuario = await buscar_usuario_com_relacionamentos(db, usuario_id)
    form = await parse_formulario_edicao(request)

    perfil_dizimista_id = (
        usuario.perfil_dizimista.id if usuario.perfil_dizimista else None
    )
    erros, numero_registro_int = await validar_formulario_edicao(
        form, db, perfil_dizimista_id=perfil_dizimista_id
    )

    paroquias = await carregar_paroquias(db)
    igrejas = await carregar_igrejas(db)

    if erros:
        return renderizar_formulario_usuario(
            request=request,
            usuario_atual=usuario_atual,
            usuario=usuario,
            erros=erros,
            paroquias=paroquias,
            igrejas=igrejas,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    try:
        dados = UsuarioUpdate(
            nome=form.nome,
            email=form.email,
            telefone=form.telefone,
            data_nascimento=form.data_nascimento,
            perfil=PerfilUsuario(form.perfil),
            paroquia_id=form.paroquia_id,
            ativo=form.ativo,
        )
    except Exception as exc:
        return renderizar_formulario_usuario(
            request=request,
            usuario_atual=usuario_atual,
            usuario=usuario,
            erros=[str(exc)],
            paroquias=paroquias,
            igrejas=igrejas,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    perfil_enum = PerfilUsuario(form.perfil)
    eh_dizimista = perfil_e_dizimista(perfil_enum, form.tambem_dizimista)

    try:
        # Se o usuário deixou de ser dizimista, remove o perfil antes.
        if not eh_dizimista:
            await remover_perfil_dizimista(db, usuario)

        perfil_payload = montar_payload_perfil_dizimista(
            eh_dizimista=eh_dizimista,
            igreja_id=form.igreja_id,
            numero_registro=numero_registro_int,
            endereco=form.endereco,
            bairro=form.bairro,
            cidade=form.cidade,
            status_cadastro=form.status_cadastro,
        )

        await atualizar_usuario(db, usuario, dados, perfil_dizimista=perfil_payload)

    except Exception as exc:
        return renderizar_formulario_usuario(
            request=request,
            usuario_atual=usuario_atual,
            usuario=usuario,
            erros=[str(exc)],
            paroquias=paroquias,
            igrejas=igrejas,
            status_code=getattr(exc, "status_code", status.HTTP_400_BAD_REQUEST),
        )

    return RedirectResponse(url="/usuarios", status_code=status.HTTP_303_SEE_OTHER)
