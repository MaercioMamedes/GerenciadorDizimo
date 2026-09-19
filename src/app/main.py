from fastapi import FastAPI

app = FastAPI(title="Gerenciador Dízimo", version="0.1.0")


@app.get("/health")
async def health_check():
    return {"status": "ok"}
