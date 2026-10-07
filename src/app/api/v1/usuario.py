from fastapi import APIRouter, Depends, Request, status
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.usuario import UsuarioCreate, UsuarioResponse
from app.services.usuario_service import criar_usuario

router = APIRouter(prefix="/usuarios", tags=["Usuários"])
templates = Jinja2Templates(directory="src/app/templates")


@router.get("/novo", status_code=status.HTTP_200_OK)
async def formulario_criar_usuario(request: Request):
    return templates.TemplateResponse(
        request,
        "usuarios/formulario.html",
        {
            "usuario": None,
            "erros": [],
            "paroquias": [],  # TODO: listar paróquias reais para o <select> do template
        },
    )


@router.post("", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
async def registrar_usuario(dados: UsuarioCreate, db: AsyncSession = Depends(get_db)):
    usuario = await criar_usuario(db, dados)
    return usuario
