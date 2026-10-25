from fastapi import Depends, FastAPI, Request
from fastapi.staticfiles import StaticFiles

from app.api.v1.auth import router as auth_api_router
from app.api.v1.paroquia import router as paroquia_api_router
from app.api.v1.usuario import router as usuario_api_router
from app.controllers.auth_controller import router as auth_views_router
from app.controllers.deps import get_usuario_atual_opcional
from app.controllers.paroquia.paroquias_controller import (
    router as paroquia_views_router,
)
from app.controllers.usuarios.router import router as usuarios_controller_router
from app.core.templates import templates

app = FastAPI(title="Gerenciador Dízimo")

app.mount("/static", StaticFiles(directory="src/app/static"), name="static")

# Views (SSR, cookie)
app.include_router(auth_views_router)
app.include_router(usuarios_controller_router)
app.include_router(paroquia_views_router)

# API (JSON)
app.include_router(auth_api_router)
app.include_router(usuario_api_router)
app.include_router(paroquia_api_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/", tags=["Home"])
async def home(
    request: Request,
    usuario_atual=Depends(get_usuario_atual_opcional),
):
    return templates.TemplateResponse(
        request, "home.html", {"usuario_atual": usuario_atual}
    )
