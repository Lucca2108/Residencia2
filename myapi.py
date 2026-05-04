from __future__ import annotations

from contextlib import asynccontextmanager

from typing import List

from fastapi import FastAPI, HTTPException, Query, Response, status

from db import init_database
from schemas import TransacaoCreate, TransacaoResponse, TransacaoUpdate, ViagemCreate, ViagemResponse, ValidacaoTransacao
from services import (
    create_transacao,
    create_viagem,
    delete_transacao,
    get_transacao_by_id,
    list_transacoes,
    search_transacoes,
    update_transacao,
    validar_transacao_cliente,
    get_viagens_por_conta
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[APP] Iniciando aplicação...")
    try:
        print("[APP] Chamando init_database()...")
        init_database()
        print("[APP] init_database() concluído com sucesso.")
    except Exception as exc:
        print(f"[APP] Falha ao inicializar banco: {exc}")
        print("[APP] A aplicação continuará subindo para fins de diagnóstico.")
    yield
    print("[APP] Encerrando aplicação...")


app = FastAPI(
    title="API de Transações",
    version="1.0.0",
    description="API FastAPI + MySQL para consulta e manutenção de transações.",
    lifespan=lifespan,
)


@app.get(
    "/transacoes",
    response_model=list[TransacaoResponse],
    summary="Listar transações",
    description="Para usar o Listar coloque em 'Limit' o número de ids que você deseja ver de uma vez, e no offset coloque o id inicial que deseja ver.",
)
def listar_transacoes(
    limit: int = Query(
        100,
        ge=1,
        le=1000,
        description="Quantidade máxima de registros retornados.",
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Quantidade de registros ignorados antes da listagem.",
    ),
):
    return list_transacoes(limit=limit, offset=offset)

@app.get(
    "/viagens/{conta}",
    response_model=list[ViagemResponse],
    status_code=status.HTTP_200_OK,
    summary="Listar viagens de uma conta",
    description="Retorna todo o histórico de viagens cadastradas para uma conta específica, ordenado das mais recentes para as mais antigas."
)
def listar_viagens(conta: str):
    viagens = get_viagens_por_conta(conta)
    return viagens

@app.get(
    "/transacoes/search",
    response_model=list[TransacaoResponse],
    summary="Buscar transações com filtros",
    description="Busca transações usando filtros opcionais.",
)
def buscar_transacoes(
    categoria: str | None = Query(
        None, description="Filtro por categoria (contém)."),
    conta: str | None = Query(None, description="Filtro por conta (contém)."),
    cidade: str | None = Query(
        None, description="Filtro por cidade (contém)."),
    estado: str | None = Query(None, description="Filtro exato por estado."),
    pais: str | None = Query(None, description="Filtro exato por país."),
    tipo_transacao: str | None = Query(
        None, description="Filtro exato por tipo de transação."),
    dispositivo: str | None = Query(
        None, description="Filtro por dispositivo (contém)."),
    estabelecimento: str | None = Query(
        None, description="Filtro por estabelecimento (contém)."),
    is_fraude: int | None = Query(
        None,
        ge=0,
        le=1,
        description="Filtro por fraude: 1 = fraude, 0 = não fraude.",
    ),
    data_inicial: str | None = Query(
        None,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Data inicial no formato YYYY-MM-DD.",
    ),
    data_final: str | None = Query(
        None,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Data final no formato YYYY-MM-DD.",
    ),
    valor_min: float | None = Query(None, description="Valor mínimo."),
    valor_max: float | None = Query(None, description="Valor máximo."),
    limit: int = Query(
        100,
        ge=1,
        le=1000,
        description="Quantidade máxima de registros retornados.",
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Quantidade de registros ignorados antes da listagem.",
    ),
):
    return search_transacoes(
        categoria=categoria,
        conta=conta,
        cidade=cidade,
        estado=estado,
        pais=pais,
        tipo_transacao=tipo_transacao,
        dispositivo=dispositivo,
        estabelecimento=estabelecimento,
        is_fraude=is_fraude,
        data_inicial=data_inicial,
        data_final=data_final,
        valor_min=valor_min,
        valor_max=valor_max,
        limit=limit,
        offset=offset,
    )


@app.get(
    "/transacoes/{transacao_id}",
    response_model=TransacaoResponse,
    summary="Buscar transação por ID",
)
def buscar_transacao_por_id(transacao_id: int):
    transacao = get_transacao_by_id(transacao_id)
    if not transacao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transação não encontrada.",
        )
    return transacao


@app.post(
    "/transacoes",
    response_model=TransacaoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar transação",
)
def criar_transacao(payload: TransacaoCreate):
    return create_transacao(payload)


@app.put(
    "/transacoes/{transacao_id}",
    response_model=TransacaoResponse,
    summary="Atualizar transação",
)
def atualizar_transacao(transacao_id: int, payload: TransacaoUpdate):
    transacao = update_transacao(transacao_id, payload)
    if not transacao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transação não encontrada.",
        )
    return transacao


@app.delete(
    "/transacoes/{transacao_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Excluir transação",
)
def excluir_transacao(transacao_id: int):
    deleted = delete_transacao(transacao_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transação não encontrada.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post(
    "/viagens",
    response_model=ViagemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar aviso de viagem",
    description="Permite ao cliente registrar previamente uma viagem para reduzir falsos positivos."
)
def registrar_viagem(payload: ViagemCreate):
    return create_viagem(payload)

@app.post(
    "/transacoes/{transacao_id}/validar",
    response_model=TransacaoResponse,
    summary="Validação do Cliente (Ação via Push/SMS)",
    description="Permite ao usuário confirmar se uma transação suspeita é legítima ou reportar como fraude confirmada."
)
def validar_transacao(transacao_id: int, payload: ValidacaoTransacao):
    transacao_atualizada = validar_transacao_cliente(transacao_id, payload.confirmada)
    if not transacao_atualizada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transação não encontrada."
        )
    return transacao_atualizada
