from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.schemas import TransacaoCreate, TransacaoResponse, TransacaoUpdate, ValidacaoTransacao
from app.services.transacao_service import (
    create_transacao,
    delete_transacao,
    get_transacao_by_id_service,
    list_transacoes,
    search_transacoes,
    update_transacao,
    validar_transacao_cliente,
)

router = APIRouter()


@router.get(
    "/transacoes",
    response_model=list[TransacaoResponse],
    summary="Listar transações",
    description="Listar transações paginadas.",
)
def listar_transacoes(
    limit: int = Query(100, ge=1, le=1000, description="Quantidade máxima de registros retornados."),
    offset: int = Query(0, ge=0, description="Quantidade de registros ignorados antes da listagem."),
):
    return list_transacoes(limit=limit, offset=offset)


@router.get(
    "/transacoes/search",
    response_model=list[TransacaoResponse],
    summary="Buscar transações com filtros",
    description="Busca transações usando filtros opcionais.",
)
def buscar_transacoes(
    categoria: str | None = Query(None, description="Filtro por categoria (contém)."),
    conta: str | None = Query(None, description="Filtro por conta (contém)."),
    cidade: str | None = Query(None, description="Filtro por cidade (contém)."),
    estado: str | None = Query(None, description="Filtro exato por estado."),
    pais: str | None = Query(None, description="Filtro exato por país."),
    tipo_transacao: str | None = Query(None, description="Filtro exato por tipo de transação."),
    dispositivo: str | None = Query(None, description="Filtro por dispositivo (contém)."),
    estabelecimento: str | None = Query(None, description="Filtro por estabelecimento (contém)."),
    is_fraude: int | None = Query(None, ge=0, le=1, description="Filtro por fraude: 1 = fraude, 0 = não fraude."),
    data_inicial: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="Data inicial no formato YYYY-MM-DD."),
    data_final: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="Data final no formato YYYY-MM-DD."),
    valor_min: float | None = Query(None, description="Valor mínimo."),
    valor_max: float | None = Query(None, description="Valor máximo."),
    limit: int = Query(100, ge=1, le=1000, description="Quantidade máxima de registros retornados."),
    offset: int = Query(0, ge=0, description="Quantidade de registros ignorados antes da listagem."),
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


@router.get(
    "/transacoes/{transacao_id}",
    response_model=TransacaoResponse,
    summary="Buscar transação por ID",
)
def buscar_transacao_por_id(transacao_id: int):
    transacao = get_transacao_by_id_service(transacao_id)
    if not transacao:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transação não encontrada.")
    return transacao


@router.post(
    "/transacoes",
    response_model=TransacaoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar transação",
)
def criar_transacao(payload: TransacaoCreate):
    return create_transacao(payload)


@router.put(
    "/transacoes/{transacao_id}",
    response_model=TransacaoResponse,
    summary="Atualizar transação",
)
def atualizar_transacao(transacao_id: int, payload: TransacaoUpdate):
    transacao = update_transacao(transacao_id, payload)
    if not transacao:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transação não encontrada.")
    return transacao


@router.delete(
    "/transacoes/{transacao_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Excluir transação",
)
def excluir_transacao(transacao_id: int):
    deleted = delete_transacao(transacao_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transação não encontrada.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/transacoes/{transacao_id}/validar",
    response_model=TransacaoResponse,
    summary="Validação do Cliente (Ação via Push/SMS)",
    description="Permite ao usuário confirmar se uma transação suspeita é legítima ou reportar como fraude confirmada.",
)
def validar_transacao(transacao_id: int, payload: ValidacaoTransacao):
    transacao_atualizada = validar_transacao_cliente(transacao_id, payload.confirmada)
    if not transacao_atualizada:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transação não encontrada.")
    return transacao_atualizada
