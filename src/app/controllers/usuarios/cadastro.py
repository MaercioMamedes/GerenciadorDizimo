"""Handlers de cadastro (criação) de usuários."""

from fastapi import Depends, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.controllers.deps import get_usuario_atual_opcional
from app.controllers.usuarios.context import (
    carregar_igrejas,
    carregar_paroquias,
    renderizar_formulario_usuario,
)
from app.controllers.usuarios.forms import parse_formulario_criacao
from app.controllers.usuarios.helpers import (
    eh_administrador,
    montar_payload_perfil_dizimista,
    perfil_e_dizimista,
)
from app.controllers.usuarios.validators import validar_formulario_criacao
from app.db.session import get_db
from app.models.perfil_dizimista import StatusCadastro
from app.models.usuario import PerfilUsuario
from app.schemas.usuario import UsuarioCreate
from app.services.usuario_service import criar_usuario


async def formulario_cadastro_usuario(
    request: Request,
    usuario_atual=Depends(get_usuario_atual_opcional),
    db: AsyncSession = Depends(get_db),
):
    paroquias = await carregar_paroquias(db)
    igrejas = await carregar_igrejas(db)

    return renderizar_formulario_usuario(
        request=request,
        usuario_atual=usuario_atual,
        usuario=None,
        erros=[],
        paroquias=paroquias,
        igrejas=igrejas,
    )


async def cadastrar_usuario_via_formulario(
    request: Request,
    usuario_atual=Depends(get_usuario_atual_opcional),
    db: AsyncSession = Depends(get_db),
):
    form = await parse_formulario_criacao(request)
    eh_admin = eh_administrador(usuario_atual)

    # Autocadastro público: força regras de negócio do RQ01.
    if not eh_admin:
        form.perfil = PerfilUsuario.DIZIMISTA.value
        form.ativo = False
        form.status_cadastro = StatusCadastro.PENDENTE.value
        form.numero_registro = None

    erros, numero_registro_int = await validar_formulario_criacao(form, eh_admin, db)

    paroquias = await carregar_paroquias(db)
    igrejas = await carregar_igrejas(db)

    if erros:
        return renderizar_formulario_usuario(
            request=request,
            usuario_atual=usuario_atual,
            usuario=None,
            erros=erros,
            paroquias=paroquias,
            igrejas=igrejas,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    try:
        perfil_enum = PerfilUsuario(form.perfil)
        dados = UsuarioCreate(
            nome=form.nome,
            email=form.email,
            senha=form.senha,
            telefone=form.telefone,
            data_nascimento=form.data_nascimento,
            perfil=perfil_enum,
            paroquia_id=form.paroquia_id,
        )
    except Exception as exc:
        return renderizar_formulario_usuario(
            request=request,
            usuario_atual=usuario_atual,
            usuario=None,
            erros=[str(exc)],
            paroquias=paroquias,
            igrejas=igrejas,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    perfil_payload = montar_payload_perfil_dizimista(
        eh_dizimista=perfil_e_dizimista(perfil_enum, form.tambem_dizimista),
        igreja_id=form.igreja_id,
        numero_registro=numero_registro_int,
        endereco=form.endereco,
        bairro=form.bairro,
        cidade=form.cidade,
        status_cadastro=form.status_cadastro,
    )

    try:
        await criar_usuario(
            db,
            dados,
            perfil_dizimista=perfil_payload,
            ativo=(eh_admin and form.ativo),
        )
    except Exception as exc:
        return renderizar_formulario_usuario(
            request=request,
            usuario_atual=usuario_atual,
            usuario=None,
            erros=[str(exc)],
            paroquias=paroquias,
            igrejas=igrejas,
            status_code=getattr(exc, "status_code", status.HTTP_400_BAD_REQUEST),
        )

    if eh_admin:
        return RedirectResponse(url="/usuarios", status_code=status.HTTP_303_SEE_OTHER)

    return RedirectResponse(
        url="/auth/login?cadastro_pendente=true",
        status_code=status.HTTP_303_SEE_OTHER,
    )
