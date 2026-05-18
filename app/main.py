from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routers.transacoes import router as transacoes_router
from app.api.routers.viagens import router as viagens_router
from app.db.init import init_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[APP] Iniciando aplicação...")
    try:
        init_database()
        print("[APP] Banco de dados inicializado com sucesso.")
    except Exception as exc:
        print(f"[APP] Falha ao inicializar o banco de dados: {exc}")
        print("[APP] Continuando a aplicação para fins de diagnóstico.")
    yield
    print("[APP] Encerrando aplicação...")


app = FastAPI(
    title="API de Transações",
    version="1.0.0",
    description="API FastAPI + MySQL para consulta e manutenção de transações.",
    lifespan=lifespan,
)

app.include_router(transacoes_router)
app.include_router(viagens_router)
