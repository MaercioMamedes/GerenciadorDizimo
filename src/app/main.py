from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.v1.auth import router as auth_router
from app.api.v1.usuario import router as usuario_router

app = FastAPI(title="Gerenciador Dízimo")

app.mount("/static", StaticFiles(directory="src/app/static"), name="static")
templates = Jinja2Templates(directory="src/app/templates")

app.include_router(auth_router)
app.include_router(usuario_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/", tags=["Home"])
async def home(request: Request):
    return templates.TemplateResponse(request=request, name="home.html", context={})
