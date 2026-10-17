from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services import paroquia_service
from app.views.deps import require_admin_view

router = APIRouter(prefix="/paroquias", tags=["Views - Paróquias"])


@router.get("/json")
async def listar_paroquias_json(
    db: AsyncSession = Depends(get_db),
    usuario_atual=Depends(require_admin_view),
):
    paroquias = await paroquia_service.listar_paroquias(db)
    return JSONResponse(content=[{"id": str(p.id), "nome": p.nome} for p in paroquias])
