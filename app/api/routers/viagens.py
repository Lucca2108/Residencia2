from __future__ import annotations

from fastapi import APIRouter, status

from app.schemas import ViagemCreate, ViagemResponse
from app.services.viagem_service import create_viagem, get_viagens_por_conta

router = APIRouter()


@router.post(
    "/viagens",
    response_model=ViagemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar aviso de viagem",
    description="Permite ao cliente registrar previamente uma viagem para reduzir falsos positivos.",
)
def registrar_viagem(payload: ViagemCreate):
    return create_viagem(payload)


@router.get(
    "/viagens/{conta}",
    response_model=list[ViagemResponse],
    summary="Listar viagens de uma conta",
    description="Retorna o histórico de viagens cadastradas para uma conta específica, ordenado das mais recentes para as mais antigas.",
)
def listar_viagens(conta: str):
    return get_viagens_por_conta(conta)
