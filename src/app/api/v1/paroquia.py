# app/api/paroquia.py
import uuid

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_admin
from app.db.session import get_db
from app.schemas.paroquia import ParoquiaCreate, ParoquiaUpdate
from app.services import paroquia_service
from app.services.paroquia_service import ParoquiaNaoEncontrada

router = APIRouter(prefix="/paroquias", tags=["paroquias-views"])
templates = Jinja2Templates(directory="app/templates")


@router.get("")
async def listar(
    request: Request,
    db: AsyncSession = Depends(get_db),
    usuario_atual=Depends(require_admin),
):
    paroquias = await paroquia_service.listar_paroquias(db)
    return templates.TemplateResponse(
        "paroquias/listar.html",
        {
            "request": request,
            "usuario_atual": usuario_atual,
            "paroquias": paroquias,
            "mensagens_flash": [],
        },
    )


@router.get("/nova")
async def formulario_criar(
    request: Request,
    usuario_atual=Depends(require_admin),
):
    return templates.TemplateResponse(
        "paroquias/formulario.html",
        {
            "request": request,
            "usuario_atual": usuario_atual,
            "paroquia": None,
            "erros": [],
            "mensagens_flash": [],
        },
    )


@router.post("/nova")
async def criar(
    request: Request,
    nome: str = Form(...),
    cnpj: str | None = Form(default=None),
    endereco: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    usuario_atual=Depends(require_admin),
):
    try:
        dados = ParoquiaCreate(nome=nome, cnpj=cnpj or None, endereco=endereco or None)
    except Exception as erro:
        return templates.TemplateResponse(
            "paroquias/formulario.html",
            {
                "request": request,
                "usuario_atual": usuario_atual,
                "paroquia": {"nome": nome, "cnpj": cnpj, "endereco": endereco},
                "erros": [str(erro)],
                "mensagens_flash": [],
            },
            status_code=422,
        )

    await paroquia_service.criar_paroquia(db, dados)
    return RedirectResponse(url="/paroquias?msg=criado", status_code=303)


@router.get("/{paroquia_id}/editar")
async def formulario_editar(
    paroquia_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    usuario_atual=Depends(require_admin),
):
    try:
        paroquia = await paroquia_service.obter_paroquia(db, paroquia_id)
    except ParoquiaNaoEncontrada:
        return RedirectResponse(url="/paroquias?msg=nao_encontrada", status_code=303)

    return templates.TemplateResponse(
        "paroquias/formulario.html",
        {
            "request": request,
            "usuario_atual": usuario_atual,
            "paroquia": paroquia,
            "erros": [],
            "mensagens_flash": [],
        },
    )


@router.post("/{paroquia_id}/editar")
async def atualizar(
    paroquia_id: uuid.UUID,
    request: Request,
    nome: str = Form(...),
    cnpj: str | None = Form(default=None),
    endereco: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    usuario_atual=Depends(require_admin),
):
    try:
        dados = ParoquiaUpdate(nome=nome, cnpj=cnpj or None, endereco=endereco or None)
        await paroquia_service.atualizar_paroquia(db, paroquia_id, dados)
    except ParoquiaNaoEncontrada:
        return RedirectResponse(url="/paroquias?msg=nao_encontrada", status_code=303)
    except Exception as erro:
        return templates.TemplateResponse(
            "paroquias/formulario.html",
            {
                "request": request,
                "usuario_atual": usuario_atual,
                "paroquia": {
                    "id": paroquia_id,
                    "nome": nome,
                    "cnpj": cnpj,
                    "endereco": endereco,
                },
                "erros": [str(erro)],
                "mensagens_flash": [],
            },
            status_code=422,
        )

    return RedirectResponse(url="/paroquias?msg=atualizado", status_code=303)
