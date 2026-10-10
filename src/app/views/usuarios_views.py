"""
View (controller) para cadastro de usuário via formulário web (UC03/UC05).

GET  /usuarios/novo  -> exibe formulário de cadastro
POST /usuarios/novo  -> processa o cadastro

TODO: quando o perfil for "dizimista", este fluxo deveria também criar um
registro em PerfilDizimista vinculado a uma igreja (RF02.5). O template atual
(`usuarios/formulario.html`) não possui campo de seleção de igreja para o
dizimista (apenas paroquia_id, exclusivo do administrador) — pendente de
ajuste no template e nesta view antes de UC03 estar 100% completo.
"""
from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.templates import templates
from app.db.session import get_db
from app.models.usuario import PerfilUsuario
from app.schemas.usuario import UsuarioCreate
from app.services.usuario_service import criar_usuario
from app.views.deps import get_usuario_atual_opcional

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
            "paroquias": [],  # TODO: listar paróquias reais para o <select> do admin
        },
    )


@router.post("/novo")
async def cadastrar_usuario_via_formulario(
    request: Request,
    nome: str = Form(...),
    email: str = Form(...),
    senha: str = Form(...),
    confirmar_senha: str = Form(...),
    perfil: PerfilUsuario = Form(...),
    telefone: str | None = Form(default=None),
    data_nascimento: str | None = Form(default=None),
    paroquia_id: str | None = Form(default=None),
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
                perfil=perfil,
                paroquia_id=paroquia_id or None,
            )
        except Exception as exc:
            # Erros de validação do Pydantic (ex.: paroquia_id obrigatório
            # para administrador, formato de e-mail, etc.)
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

    return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)
