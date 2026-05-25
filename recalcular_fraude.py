from __future__ import annotations

from app.domain.fraude import avaliar_fraude
from app.domain.ml import prever_anomalia
from app.repositories.transacao_repository import (
    get_estatisticas_conta,
    get_frequencia_recente,
    list_transacoes,
    update_transacao_record,
)
from app.repositories.viagem_repository import get_viagem_ativa_por_conta


def _transacao_em_viagem_legitima(conta: str, pais: str, estado: str | None, data: str) -> bool:
    viagens_ativas = get_viagem_ativa_por_conta(conta, data)
    pais = str(pais or "").strip().lower()
    estado = str(estado or "").strip().lower()

    for viagem in viagens_ativas:
        pais_destino = str(viagem.get("pais_destino", "")).strip().lower()
        estado_destino = str(viagem.get("estado_destino", "")).strip().lower()
        if pais and pais == pais_destino:
            return True
        if estado and estado == estado_destino:
            return True

    return False


def recalcular_todas_transacoes(limit: int = 1000000, offset: int = 0) -> int:
    transacoes = list_transacoes(limit=limit, offset=offset)
    updated = 0

    for transacao in transacoes:
        hora = transacao.get("hora")
        media_hist = get_estatisticas_conta(transacao["conta"])
        freq = get_frequencia_recente(transacao["conta"], transacao["data"], hora, minutos=30)
        em_viagem_legitima = _transacao_em_viagem_legitima(
            transacao["conta"], transacao["pais"], transacao.get("estado"), transacao["data"]
        )
        resultado_ia = prever_anomalia(transacao)
        analise = avaliar_fraude(
            transacao,
            media_historica=media_hist,
            frequencia_recente=freq,
            em_viagem=em_viagem_legitima,
            resultado_ml=resultado_ia,
        )

        values = {**transacao}
        values["is_fraude"] = 1 if analise["is_fraude"] else 0
        values["status_validacao"] = "pendente" if analise["is_fraude"] else "aprovada"

        if update_transacao_record(transacao["id"], values):
            updated += 1

    return updated


if __name__ == "__main__":
    count = recalcular_todas_transacoes()
    print(f"Recalculadas {count} transações.")
