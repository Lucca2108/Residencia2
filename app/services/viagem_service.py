from __future__ import annotations

from app.repositories.viagem_repository import create_viagem_record, get_viagens_por_conta as _get_viagens_por_conta
from app.schemas import ViagemCreate


def create_viagem(payload: ViagemCreate) -> dict[str, object]:
    viagem_id = create_viagem_record(payload.model_dump())
    return {
        "id": viagem_id,
        "conta": payload.conta,
        "cidade_destino": payload.cidade_destino,
        "estado_destino": payload.estado_destino,
        "pais_destino": payload.pais_destino,
        "data_inicio": payload.data_inicio,
        "data_fim": payload.data_fim,
    }


def get_viagens_por_conta(conta: str) -> list[dict[str, object]]:
    return _get_viagens_por_conta(conta)
