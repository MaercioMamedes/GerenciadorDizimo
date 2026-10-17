from fastapi import APIRouter, Depends, Form, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.templates import templates
from app.db.session import get_db
from app.services.auth_service import (
    autenticar_usuario,
    gerar_token_para_usuario,
    registrar_logout,
)
from app.views.deps import NOME_COOKIE_TOKEN, get_usuario_atual_opcional

router = APIRouter(prefix="/auth", tags=["Views - Autenticação"])

MENSAGEM_CADASTRO_PENDENTE = (
    "Sua conta ainda não está ativa. Aguarde a validação de um administrador "
    "para poder acessar o sistema."
)


@router.get("/login")
async def formulario_login(
    request: Request,
    usuario_atual=Depends(get_usuario_atual_opcional),
    cadastro_pendente: bool = Query(default=False),
):
    if usuario_atual:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    aviso = MENSAGEM_CADASTRO_PENDENTE if cadastro_pendente else None

    return templates.TemplateResponse(
        request,
        "auth/login.html",
        {"usuario_atual": None, "erro": None, "aviso": aviso},
    )


@router.post("/login")
async def login_via_formulario(
    request: Request,
    email: str = Form(...),
    senha: str = Form(...),
    next: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
):
    ip_origem = request.client.host if request.client else None
    try:
        usuario = await autenticar_usuario(
            db, email=email, senha=senha, ip_origem=ip_origem
        )
    except Exception as exc:
        detail = str(getattr(exc, "detail", exc))
        status_code = getattr(exc, "status_code", None)

        if status_code == status.HTTP_403_FORBIDDEN:
            if "desativada" in detail.lower():
                return templates.TemplateResponse(
                    request,
                    "auth/login.html",
                    {
                        "usuario_atual": None,
                        "erro": None,
                        "aviso": MENSAGEM_CADASTRO_PENDENTE,
                    },
                    status_code=status.HTTP_403_FORBIDDEN,
                )

            return templates.TemplateResponse(
                request,
                "auth/login.html",
                {"usuario_atual": None, "erro": detail.strip(), "aviso": None},
                status_code=status.HTTP_403_FORBIDDEN,
            )

        return templates.TemplateResponse(
            request,
            "auth/login.html",
            {"usuario_atual": None, "erro": "Email ou senha inválidos.", "aviso": None},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    token = gerar_token_para_usuario(usuario)
    destino = next or "/"

    resposta = RedirectResponse(url=destino, status_code=status.HTTP_303_SEE_OTHER)
    resposta.set_cookie(
        key=NOME_COOKIE_TOKEN,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=3600,
    )
    return resposta


@router.get("/logout")
async def logout_via_formulario(
    request: Request,
    db: AsyncSession = Depends(get_db),
    usuario_atual=Depends(get_usuario_atual_opcional),
):
    if usuario_atual:
        ip_origem = request.client.host if request.client else None
        await registrar_logout(db, usuario=usuario_atual, ip_origem=ip_origem)

    resposta = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    resposta.delete_cookie(NOME_COOKIE_TOKEN)
    return resposta
