"""
View (controller) para cadastro, listagem e edição de usuário via formulário
web (UC03/UC04/UC05).
"""

import math
import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.templates import templates
from app.db.session import get_db
from app.models.igreja import Igreja
from app.models.paroquia import Paroquia
from app.models.perfil_dizimista import PerfilDizimista, StatusCadastro
from app.models.usuario import PerfilUsuario, Usuario
from app.schemas.usuario import UsuarioCreate, UsuarioUpdate
from app.services.usuario_service import (
    atualizar_usuario,
    criar_usuario,
    excluir_usuario,
)
from app.views.deps import (
    get_usuario_atual_opcional,
    require_admin_view,
)

router = APIRouter(prefix="/usuarios", tags=["Views - Usuários"])


@router.get("/novo")
async def formulario_cadastro_usuario(
    request: Request,
    usuario_atual=Depends(get_usuario_atual_opcional),
):
    return templates.TemplateResponse(
        request,
        "usuarios/formulario.html",
        {
            "usuario_atual": usuario_atual,
            "usuario": None,
            "erros": [],
            "paroquias": [],
        },
    )


@router.post("/novo")
async def cadastrar_usuario_via_formulario(
    request: Request,
    nome: str = Form(...),
    email: str = Form(...),
    senha: str = Form(...),
    confirmar_senha: str = Form(...),
    telefone: str | None = Form(default=None),
    data_nascimento: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
):
    erros: list[str] = []

    if senha != confirmar_senha:
        erros.append("As senhas informadas não coincidem.")

    dados: UsuarioCreate | None = None
    if not erros:
        try:
            dados = UsuarioCreate(
                nome=nome,
                email=email,
                senha=senha,
                telefone=telefone or None,
                data_nascimento=data_nascimento or None,
            )
        except Exception as exc:
            erros.append(str(exc))

    if erros:
        return templates.TemplateResponse(
            request,
            "usuarios/formulario.html",
            {
                "usuario_atual": None,
                "usuario": None,
                "erros": erros,
                "paroquias": [],
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    try:
        await criar_usuario(db, dados)
    except Exception as exc:
        detail = getattr(exc, "detail", str(exc))
        return templates.TemplateResponse(
            request,
            "usuarios/formulario.html",
            {
                "usuario_atual": None,
                "usuario": None,
                "erros": [detail],
                "paroquias": [],
            },
            status_code=getattr(exc, "status_code", status.HTTP_400_BAD_REQUEST),
        )

    return RedirectResponse(
        url="/auth/login?cadastro_pendente=true", status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("")
async def listar_usuarios_view(
    request: Request,
    pagina: int = 1,
    tamanho_pagina: int = 10,
    perfil: str | None = None,  # <- trocado de PerfilUsuario | None para str | None
    usuario_atual=Depends(require_admin_view),
    db: AsyncSession = Depends(get_db),
):
    # Normaliza: "" (vindo do <option value="">Todos</option>)
    #  é tratado como "sem filtro"
    perfil_enum: PerfilUsuario | None = None
    if perfil:
        try:
            perfil_enum = PerfilUsuario(perfil)
        except ValueError:
            perfil_enum = None

    resultado = await listar_usuarios_paginado(
        db, pagina=pagina, tamanho_pagina=tamanho_pagina, perfil=perfil_enum
    )

    print(perfil_enum)  # DEBUG

    return templates.TemplateResponse(
        request,
        "usuarios/lista.html",
        {
            "usuario_atual": usuario_atual,
            "perfil_filtro": perfil_enum.value if perfil_enum else "",
            **resultado,
        },
    )


# IMPORTANTE: esta rota precisa vir ANTES de "/{usuario_id}/editar"
@router.get("/{usuario_id}")
async def detalhes_usuario_view(
    request: Request,
    usuario_id: uuid.UUID,
    usuario_atual=Depends(require_admin_view),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Usuario)
        .where(Usuario.id == usuario_id)
        .options(
            selectinload(Usuario.paroquia).selectinload(Paroquia.igrejas),
            selectinload(Usuario.perfil_dizimista).selectinload(PerfilDizimista.igreja),
        )
    )
    resultado = await db.execute(stmt)
    usuario = resultado.scalar_one_or_none()
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado."
        )

    return templates.TemplateResponse(
        request,
        "usuarios/detalhes.html",
        {
            "usuario_atual": usuario_atual,
            "usuario": usuario,
        },
    )


@router.get("/{usuario_id}/editar")
async def formulario_editar_usuario(
    request: Request,
    usuario_id: uuid.UUID,
    usuario_atual=Depends(require_admin_view),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Usuario)
        .where(Usuario.id == usuario_id)
        .options(
            selectinload(Usuario.paroquia).selectinload(Paroquia.igrejas),
            selectinload(Usuario.perfil_dizimista),
        )
    )
    resultado = await db.execute(stmt)
    usuario = resultado.scalar_one_or_none()
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado."
        )

    igrejas = (await db.execute(select(Igreja).order_by(Igreja.nome))).scalars().all()

    return templates.TemplateResponse(
        request,
        "usuarios/formulario.html",
        {
            "usuario_atual": usuario_atual,
            "usuario": usuario,
            "erros": [],
            "paroquias": [],  # TODO: listar paróquias reais para o <select>
            "igrejas": igrejas,
        },
    )


@router.post("/{usuario_id}/editar")
async def editar_usuario_via_formulario(
    request: Request,
    usuario_id: uuid.UUID,
    nome: str = Form(...),
    email: str = Form(...),
    telefone: str | None = Form(default=None),
    data_nascimento: str | None = Form(default=None),
    perfil: PerfilUsuario = Form(...),
    paroquia_id: str | None = Form(default=None),
    ativo: bool = Form(default=False),
    tambem_dizimista: bool = Form(default=False),
    igreja_id: str | None = Form(default=None),
    endereco: str | None = Form(default=None),
    bairro: str | None = Form(default=None),
    cidade: str | None = Form(default=None),
    status_cadastro: StatusCadastro | None = Form(default=None),
    usuario_atual=Depends(require_admin_view),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Usuario)
        .where(Usuario.id == usuario_id)
        .options(
            selectinload(Usuario.paroquia).selectinload(Paroquia.igrejas),
            selectinload(Usuario.perfil_dizimista),
        )
    )
    resultado = await db.execute(stmt)
    usuario = resultado.scalar_one_or_none()
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado."
        )

    igrejas = (await db.execute(select(Igreja).order_by(Igreja.nome))).scalars().all()

    erros: list[str] = []
    dados: UsuarioUpdate | None = None
    try:
        dados = UsuarioUpdate(
            nome=nome,
            email=email,
            telefone=telefone or None,
            data_nascimento=data_nascimento or None,
            perfil=perfil,
            paroquia_id=paroquia_id or None,
            ativo=ativo,
        )
    except Exception as exc:
        erros.append(str(exc))

    # Validação específica do perfil de dizimista "extra"
    if tambem_dizimista and not igreja_id:
        erros.append("Selecione a igreja para o perfil de Dizimista.")

    if erros:
        return templates.TemplateResponse(
            request,
            "usuarios/formulario.html",
            {
                "usuario_atual": usuario_atual,
                "usuario": usuario,
                "erros": erros,
                "paroquias": [],
                "igrejas": igrejas,
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    try:
        await atualizar_usuario(db, usuario, dados)

        # Sincroniza o perfil de Dizimista (independente do campo `perfil` de RBAC)
        if tambem_dizimista:
            if usuario.perfil_dizimista is None:
                novo_perfil_dizimista = PerfilDizimista(
                    usuario_id=usuario.id,
                    igreja_id=uuid.UUID(igreja_id),
                    endereco=endereco or None,
                    bairro=bairro or None,
                    cidade=cidade or None,
                    status_cadastro=status_cadastro or StatusCadastro.PENDENTE,
                )
                db.add(novo_perfil_dizimista)
            else:
                usuario.perfil_dizimista.igreja_id = uuid.UUID(igreja_id)
                usuario.perfil_dizimista.endereco = endereco or None
                usuario.perfil_dizimista.bairro = bairro or None
                usuario.perfil_dizimista.cidade = cidade or None
                if status_cadastro:
                    usuario.perfil_dizimista.status_cadastro = status_cadastro
        else:
            if usuario.perfil_dizimista is not None:
                await db.delete(usuario.perfil_dizimista)

        await db.commit()
    except Exception as exc:
        detail = getattr(exc, "detail", str(exc))
        return templates.TemplateResponse(
            request,
            "usuarios/formulario.html",
            {
                "usuario_atual": usuario_atual,
                "usuario": usuario,
                "erros": [detail],
                "paroquias": [],
                "igrejas": igrejas,
            },
            status_code=getattr(exc, "status_code", status.HTTP_400_BAD_REQUEST),
        )

    return RedirectResponse(url="/usuarios", status_code=status.HTTP_303_SEE_OTHER)


async def listar_usuarios_paginado(
    db: AsyncSession,
    pagina: int = 1,
    tamanho_pagina: int = 10,
    perfil: PerfilUsuario | None = None,
) -> dict:
    pagina = max(pagina, 1)
    tamanho_pagina = max(min(tamanho_pagina, 100), 1)

    filtro = []
    if perfil == PerfilUsuario.DIZIMISTA:
        # Retorna dizimistas puros OU administradores que também são dizimistas
        filtro.append(
            or_(
                Usuario.perfil == PerfilUsuario.DIZIMISTA,
                Usuario.perfil_dizimista.has()
            )
        )
    elif perfil == PerfilUsuario.ADMINISTRADOR:
        filtro.append(Usuario.perfil == PerfilUsuario.ADMINISTRADOR)

    total_registros = (
        await db.execute(select(func.count()).select_from(Usuario).where(*filtro))
    ).scalar_one()

    total_paginas = max(math.ceil(total_registros / tamanho_pagina), 1)
    pagina = min(pagina, total_paginas)

    resultado = await db.execute(
        select(Usuario)
        .where(*filtro)
        .options(selectinload(Usuario.perfil_dizimista))
        .order_by(Usuario.nome)
        .offset((pagina - 1) * tamanho_pagina)
        .limit(tamanho_pagina)
    )
    itens = resultado.scalars().all()

    return {
        "itens": itens,
        "pagina": pagina,
        "tamanho_pagina": tamanho_pagina,
        "total_registros": total_registros,
        "total_paginas": total_paginas,
    }


@router.post("/{usuario_id}/excluir")
async def excluir_usuario_via_formulario(
    request: Request,
    usuario_id: uuid.UUID,
    usuario_atual=Depends(get_usuario_atual_opcional),
    db: AsyncSession = Depends(get_db),
):
    if usuario_atual is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="É necessário estar autenticado.",
        )

    # Regra de permissão: apenas admin ou o próprio usuário podem excluir.
    if usuario_atual.perfil == PerfilUsuario.ADMINISTRADOR:

        stmt = (
            select(Usuario)
            .where(Usuario.id == usuario_id)
            .options(selectinload(Usuario.perfil_dizimista))
        )
        resultado = await db.execute(stmt)
        usuario = resultado.scalar_one_or_none()

        if usuario is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado."
            )

        await excluir_usuario(db, usuario)

        return RedirectResponse(url="/usuarios", status_code=status.HTTP_303_SEE_OTHER)

    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para excluir este usuário.",
        )
