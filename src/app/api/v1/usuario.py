from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.usuario import UsuarioCreate, UsuarioResponse
from app.services.usuario_service import criar_usuario

router = APIRouter(prefix="/usuarios", tags=["Usuários"])


@router.post("", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
async def registrar_usuario(dados: UsuarioCreate, db: AsyncSession = Depends(get_db)):
    usuario = await criar_usuario(db, dados)
    return usuario
