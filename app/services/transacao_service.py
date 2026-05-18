from __future__ import annotations

from app.domain.fraude import avaliar_fraude
from app.domain.ml import prever_anomalia
from app.repositories.transacao_repository import (
    create_transacao_record,
    delete_transacao as _delete_transacao,
    get_estatisticas_conta,
    get_frequencia_recente,
    get_transacao_by_id,
    list_transacoes as _list_transacoes,
    search_transacoes as _search_transacoes,
    update_transacao_record,
)
from app.repositories.viagem_repository import get_viagem_ativa_por_conta
from app.schemas import TransacaoCreate, TransacaoUpdate


def _format_payload_hora(hora: str) -> str:
    return hora if len(hora) == 8 else f"{hora}:00"


def list_transacoes(limit: int = 100, offset: int = 0):
    return _list_transacoes(limit=limit, offset=offset)


def get_transacao_by_id_service(transacao_id: int):
    return get_transacao_by_id(transacao_id)


def search_transacoes(**filters):
    return _search_transacoes(**filters)


def create_transacao(payload: TransacaoCreate):
    hora_formatada = _format_payload_hora(payload.hora)
    media_hist = get_estatisticas_conta(payload.conta)
    freq = get_frequencia_recente(payload.conta, payload.data, hora_formatada, minutos=30)
    viagens_ativas = get_viagem_ativa_por_conta(payload.conta, payload.data)

    em_viagem_legitima = False
    for viagem in viagens_ativas:
        pais_destino = str(viagem.get("pais_destino", "")).strip().lower()
        estado_destino = str(viagem.get("estado_destino", "")).strip().lower()
        if payload.pais.lower() == pais_destino:
            em_viagem_legitima = True
            break
        if payload.estado and payload.estado.lower() == estado_destino:
            em_viagem_legitima = True
            break

    resultado_ia = prever_anomalia(payload.model_dump())
    analise_fraude = avaliar_fraude(
        payload,
        media_historica=media_hist,
        frequencia_recente=freq,
        em_viagem=em_viagem_legitima,
        resultado_ml=resultado_ia,
    )

    values = payload.model_dump()
    values["hora"] = hora_formatada
    values["is_fraude"] = 1 if analise_fraude["is_fraude"] else 0
    values["status_validacao"] = "pendente" if values["is_fraude"] == 1 else "aprovada"

    if values["status_validacao"] == "pendente":
        print("⚠️ [ALERTA ANTIFRAUDE] Transação suspeita detectada!")
        print(f"📱 Disparando Push Notification/SMS para o cliente da conta {payload.conta}...")
        print(f"Motivos: {', '.join(analise_fraude['motivos'])}")

    transacao_id = create_transacao_record(values)
    return get_transacao_by_id(transacao_id)


def update_transacao(transacao_id: int, payload: TransacaoUpdate):
    existing = get_transacao_by_id(transacao_id)
    if not existing:
        return None

    analise_fraude = avaliar_fraude(payload)
    values = payload.model_dump()
    values["hora"] = _format_payload_hora(payload.hora)
    values["is_fraude"] = 1 if analise_fraude["is_fraude"] else 0
    values["status_validacao"] = existing.get("status_validacao", "aprovada")

    success = update_transacao_record(transacao_id, values)
    return get_transacao_by_id(transacao_id) if success else None


def delete_transacao(transacao_id: int) -> bool:
    return _delete_transacao(transacao_id)


def validar_transacao_cliente(transacao_id: int, confirmada: bool):
    transacao = get_transacao_by_id(transacao_id)
    if not transacao:
        return None

    novo_status = "confirmada_pelo_cliente" if confirmada else "fraude_confirmada"
    is_fraude_atualizado = 0 if confirmada else 1
    values = {**transacao, "is_fraude": is_fraude_atualizado, "status_validacao": novo_status}

    update_transacao_record(transacao_id, values)
    return get_transacao_by_id(transacao_id)
