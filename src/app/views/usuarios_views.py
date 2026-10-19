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
from app.services.perfil_dizimista_service import validar_numero_registro_unico
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


async def _carregar_paroquias(db: AsyncSession) -> list[Paroquia]:
    """
    Retorna as paróquias com a relationship de igrejas carregada,
    necessária para que a property Paroquia.nome funcione no template.
    """
    resultado = await db.execute(
        select(Paroquia).options(selectinload(Paroquia.igrejas)).order_by(Paroquia.id)
    )
    return list(resultado.scalars().all())


async def _carregar_igrejas(db: AsyncSession) -> list[Igreja]:
    return list(
        (await db.execute(select(Igreja).order_by(Igreja.nome))).scalars().all()
    )


def _render_formulario(
    request: Request,
    usuario_atual,
    usuario: Usuario | None,
    erros: list[str],
    paroquias: list[Paroquia],
    igrejas: list[Igreja],
    status_code: int = status.HTTP_200_OK,
):
    return templates.TemplateResponse(
        request,
        "usuarios/formulario.html",
        {
            "usuario_atual": usuario_atual,
            "usuario": usuario,
            "erros": erros,
            "paroquias": paroquias,
            "igrejas": igrejas,
        },
        status_code=status_code,
    )


def _parse_numero_registro(valor: str | None) -> tuple[int | None, str | None]:
    """Converte o valor do formulário em int ou retorna erro."""
    if not valor or not valor.strip():
        return None, None
    try:
        numero = int(valor.strip())
        if numero < 1:
            return None, "Número de registro deve ser maior que zero."
        return numero, None
    except ValueError:
        return None, "Número de registro deve ser um número inteiro positivo."


@router.get("/novo")
async def formulario_cadastro_usuario(
    request: Request,
    usuario_atual=Depends(get_usuario_atual_opcional),
    db: AsyncSession = Depends(get_db),
):
    igrejas = await _carregar_igrejas(db)
    paroquias = await _carregar_paroquias(db)

    return _render_formulario(
        request=request,
        usuario_atual=usuario_atual,
        usuario=None,
        erros=[],
        paroquias=paroquias,
        igrejas=igrejas,
    )


@router.post("/novo")
async def cadastrar_usuario_via_formulario(
    request: Request,
    nome: str = Form(...),
    email: str | None = Form(default=None),
    senha: str | None = Form(default=None),
    confirmar_senha: str | None = Form(default=None),
    telefone: str | None = Form(default=None),
    data_nascimento: str | None = Form(default=None),
    perfil: str = Form(default="dizimista"),
    paroquia_id: str | None = Form(default=None),
    ativo: bool = Form(default=False),
    tambem_dizimista: bool = Form(default=False),
    igreja_id: str | None = Form(default=None),
    numero_registro: str | None = Form(default=None),
    endereco: str | None = Form(default=None),
    bairro: str | None = Form(default=None),
    cidade: str | None = Form(default=None),
    status_cadastro: str = Form(default="pendente"),
    usuario_atual=Depends(get_usuario_atual_opcional),
    db: AsyncSession = Depends(get_db),
):
    erros: list[str] = []
    igrejas = await _carregar_igrejas(db)
    paroquias = await _carregar_paroquias(db)

    eh_admin = (
        usuario_atual is not None
        and usuario_atual.perfil == PerfilUsuario.ADMINISTRADOR
    )

    # CASO 1: autocadastro público força perfil dizimista e inativo
    if not eh_admin:
        perfil = PerfilUsuario.DIZIMISTA.value
        ativo = False
        status_cadastro = StatusCadastro.PENDENTE.value

    try:
        perfil_enum = PerfilUsuario(perfil)
    except ValueError:
        perfil_enum = PerfilUsuario.DIZIMISTA

    eh_dizimista = (perfil_enum == PerfilUsuario.DIZIMISTA) or (
        perfil_enum == PerfilUsuario.ADMINISTRADOR and tambem_dizimista
    )

    # Validações conforme o perfil
    if perfil_enum == PerfilUsuario.ADMINISTRADOR:
        if not email:
            erros.append("E-mail é obrigatório para o perfil Administrador.")
        if not senha:
            erros.append("Senha é obrigatória para o perfil Administrador.")
        if not paroquia_id:
            erros.append("Paróquia é obrigatória para o perfil Administrador.")
    elif not eh_admin:
        # CASO 1: autocadastro exige e-mail/senha
        if not email:
            erros.append("E-mail é obrigatório para o cadastro.")
        if not senha:
            erros.append("Senha é obrigatória para o cadastro.")

    if senha and confirmar_senha and senha != confirmar_senha:
        erros.append("As senhas informadas não coincidem.")

    if eh_dizimista and not igreja_id:
        erros.append("Selecione a igreja para o perfil de Dizimista.")

    numero_registro_int, erro_numero = _parse_numero_registro(numero_registro)
    if erro_numero:
        erros.append(erro_numero)

    if numero_registro_int and eh_dizimista:
        try:
            await validar_numero_registro_unico(db, numero_registro_int)
        except Exception as exc:
            erros.append(str(exc))

    dados: UsuarioCreate | None = None
    if not erros:
        try:
            dados = UsuarioCreate(
                nome=nome,
                email=email or None,
                senha=senha or None,
                telefone=telefone or None,
                data_nascimento=data_nascimento or None,
                perfil=perfil_enum,
                paroquia_id=paroquia_id or None,
            )
        except Exception as exc:
            erros.append(str(exc))

    if erros:
        return _render_formulario(
            request=request,
            usuario_atual=usuario_atual,
            usuario=None,
            erros=erros,
            paroquias=paroquias,
            igrejas=igrejas,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    try:
        usuario = await criar_usuario(db, dados)

        if eh_dizimista and igreja_id:
            perfil_diz = PerfilDizimista(
                usuario_id=usuario.id,
                igreja_id=uuid.UUID(igreja_id),
                numero_registro=numero_registro_int,
                endereco=endereco or None,
                bairro=bairro or None,
                cidade=cidade or None,
                status_cadastro=StatusCadastro(status_cadastro)
                if status_cadastro
                else StatusCadastro.PENDENTE,
            )
            db.add(perfil_diz)

        # Se admin criou ativo, aplica após a criação (modelo nasce inativo)
        if eh_admin and ativo:
            usuario.ativo = True

        await db.commit()
        await db.refresh(usuario)

    except Exception as exc:
        await db.rollback()
        detail = getattr(exc, "detail", str(exc))
        return _render_formulario(
            request=request,
            usuario_atual=usuario_atual,
            usuario=None,
            erros=[detail],
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


@router.get("")
async def listar_usuarios_view(
    request: Request,
    pagina: int = 1,
    tamanho_pagina: int = 10,
    perfil: str | None = None,
    usuario_atual=Depends(require_admin_view),
    db: AsyncSession = Depends(get_db),
):
    perfil_enum: PerfilUsuario | None = None
    if perfil:
        try:
            perfil_enum = PerfilUsuario(perfil)
        except ValueError:
            perfil_enum = None

    resultado = await listar_usuarios_paginado(
        db, pagina=pagina, tamanho_pagina=tamanho_pagina, perfil=perfil_enum
    )

    return templates.TemplateResponse(
        request,
        "usuarios/lista.html",
        {
            "usuario_atual": usuario_atual,
            "perfil_filtro": perfil_enum.value if perfil_enum else "",
            **resultado,
        },
    )


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

    igrejas = await _carregar_igrejas(db)
    paroquias = await _carregar_paroquias(db)

    return _render_formulario(
        request=request,
        usuario_atual=usuario_atual,
        usuario=usuario,
        erros=[],
        paroquias=paroquias,
        igrejas=igrejas,
    )


@router.post("/{usuario_id}/editar")
async def editar_usuario_via_formulario(
    request: Request,
    usuario_id: uuid.UUID,
    nome: str = Form(...),
    email: str | None = Form(default=None),
    telefone: str | None = Form(default=None),
    data_nascimento: str | None = Form(default=None),
    perfil: PerfilUsuario = Form(...),
    paroquia_id: str | None = Form(default=None),
    ativo: bool = Form(default=False),
    tambem_dizimista: bool = Form(default=False),
    igreja_id: str | None = Form(default=None),
    numero_registro: str | None = Form(default=None),
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

    igrejas = await _carregar_igrejas(db)
    paroquias = await _carregar_paroquias(db)

    erros: list[str] = []

    if perfil == PerfilUsuario.ADMINISTRADOR and not paroquia_id:
        erros.append("Paróquia é obrigatória para o perfil Administrador.")

    eh_dizimista = (perfil == PerfilUsuario.DIZIMISTA) or (
        perfil == PerfilUsuario.ADMINISTRADOR and tambem_dizimista
    )

    if eh_dizimista and not igreja_id:
        erros.append("Selecione a igreja para o perfil de Dizimista.")

    numero_registro_int, erro_numero = _parse_numero_registro(numero_registro)
    if erro_numero:
        erros.append(erro_numero)

    if numero_registro_int and eh_dizimista:
        try:
            perfil_dizimista_id = (
                usuario.perfil_dizimista.id if usuario.perfil_dizimista else None
            )
            await validar_numero_registro_unico(
                db, numero_registro_int, perfil_id=perfil_dizimista_id
            )
        except Exception as exc:
            erros.append(str(exc))

    dados: UsuarioUpdate | None = None
    if not erros:
        try:
            dados = UsuarioUpdate(
                nome=nome,
                email=email or None,
                telefone=telefone or None,
                data_nascimento=data_nascimento or None,
                perfil=perfil,
                paroquia_id=paroquia_id or None,
                ativo=ativo,
            )
        except Exception as exc:
            erros.append(str(exc))

    if erros:
        return _render_formulario(
            request=request,
            usuario_atual=usuario_atual,
            usuario=usuario,
            erros=erros,
            paroquias=paroquias,
            igrejas=igrejas,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    try:
        await atualizar_usuario(db, usuario, dados)

        if eh_dizimista:
            igreja_uuid = uuid.UUID(igreja_id) if igreja_id else None
            if usuario.perfil_dizimista is None:
                if igreja_uuid:
                    novo_perfil_dizimista = PerfilDizimista(
                        usuario_id=usuario.id,
                        igreja_id=igreja_uuid,
                        numero_registro=numero_registro_int,
                        endereco=endereco or None,
                        bairro=bairro or None,
                        cidade=cidade or None,
                        status_cadastro=status_cadastro or StatusCadastro.PENDENTE,
                    )
                    db.add(novo_perfil_dizimista)
            else:
                if igreja_uuid:
                    usuario.perfil_dizimista.igreja_id = igreja_uuid
                usuario.perfil_dizimista.numero_registro = numero_registro_int
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
        await db.rollback()
        detail = getattr(exc, "detail", str(exc))
        return _render_formulario(
            request=request,
            usuario_atual=usuario_atual,
            usuario=usuario,
            erros=[detail],
            paroquias=paroquias,
            igrejas=igrejas,
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
        filtro.append(
            or_(
                Usuario.perfil == PerfilUsuario.DIZIMISTA,
                Usuario.perfil_dizimista.has(),
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
