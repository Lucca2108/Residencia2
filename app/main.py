from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers.transacoes import router as transacoes_router
from app.api.routers.viagens import router as viagens_router
from app.db.init import init_database
from app.domain.fraude import avaliar_fraude
from app.domain.ml import prever_anomalia
from app.schemas import AnaliseTransacaoRequest
from app.services.transacao_service import get_dashboard_summary


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get(
    "/transacoes/dashboard",
    summary="Resumo do dashboard",
    description="Retorna os agregados calculados para alimentar os gráficos do frontend.",
)
def dashboard_transacoes():
    return get_dashboard_summary()


app.include_router(transacoes_router)
app.include_router(viagens_router)


@app.get("/", summary="Status da API")
def root() -> dict[str, str]:
    return {
        "status": "ok",
        "message": "API de Transações em execução",
        "docs": "/docs",
    }


@app.post(
    "/analisar",
    summary="Analisar transação sem persistir",
    description="Executa a lógica de fraude e ML sobre uma transação recebida e retorna apenas o diagnóstico.",
    responses={
        200: {
            "description": "Diagnóstico calculado com sucesso.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "mensagem": "Análise concluída com sucesso.",
                        "transacao": {
                            "valor": 120.5,
                            "data": "2026-05-18",
                            "hora": "14:30:00",
                            "conta": "12345-6",
                            "pais": "Brasil",
                            "tipo_transacao": "debito",
                            "dispositivo": "android",
                            "tentativas": 1,
                            "categoria": "geral",
                            "cidade": "nao_informada",
                            "estado": None,
                            "estabelecimento": "nao_informado",
                            "dia_semana": "nao_informado",
                            "latitude": None,
                            "longitude": None,
                            "ip_origem": "0.0.0.0",
                        },
                        "is_fraude": False,
                        "score": 0,
                        "classificacao_risco": "baixo",
                        "motivos": [],
                        "resultado_ml": {
                            "is_anomalia_ml": False,
                            "score_ml": 0.0,
                        },
                        "decisao": "normal",
                    }
                }
            },
        }
    },
)
def analisar_transacao(payload: AnaliseTransacaoRequest) -> dict[str, Any]:
    dados = payload.model_dump()
    resultado_ml = prever_anomalia(dados)
    resultado_fraude = avaliar_fraude(
        dados,
        resultado_ml=resultado_ml,
    )

    return {
        "success": True,
        "mensagem": "Análise concluída com sucesso.",
        "transacao": dados,
        "is_fraude": resultado_fraude["is_fraude"],
        "score": resultado_fraude["score"],
        "classificacao_risco": resultado_fraude["classificacao_risco"],
        "motivos": resultado_fraude["motivos"],
        "resultado_ml": resultado_ml,
        "decisao": "fraude" if resultado_fraude["is_fraude"] else "normal",
    }
