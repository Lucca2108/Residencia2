from __future__ import annotations

from datetime import time
from typing import Any


def _to_dict(transacao: Any) -> dict[str, Any]:
    if isinstance(transacao, dict):
        return transacao

    if hasattr(transacao, "model_dump"):
        return transacao.model_dump()

    if hasattr(transacao, "dict"):
        return transacao.dict()

    raise TypeError(
        "Tipo de transação não suportado para avaliação de fraude.")


def _normalizar_texto(valor: Any) -> str:
    if valor is None:
        return ""
    return str(valor).strip().lower()


def _to_float(valor: Any, default: float = 0.0) -> float:
    if valor is None or valor == "":
        return default
    try:
        return float(valor)
    except (TypeError, ValueError):
        return default


def _to_int(valor: Any, default: int = 0) -> int:
    if valor is None or valor == "":
        return default
    try:
        return int(valor)
    except (TypeError, ValueError):
        return default


def _parse_hora(valor: Any) -> time | None:
    if valor is None:
        return None

    texto = str(valor).strip()

    try:
        if len(texto) == 5:
            hora, minuto = texto.split(":")
            return time(hour=int(hora), minute=int(minuto), second=0)

        if len(texto) == 8:
            hora, minuto, segundo = texto.split(":")
            return time(hour=int(hora), minute=int(minuto), second=int(segundo))
    except (ValueError, TypeError):
        return None

    return None


def avaliar_fraude(transacao: Any, media_historica: float = 0.0, frequencia_recente: int = 0, em_viagem: bool = False, resultado_ml: dict[str, Any] = None) -> dict[str, Any]:
    dados = _to_dict(transacao)

    score = 0
    motivos: list[str] = []

    resultado_ml = resultado_ml or {}

    valor = _to_float(dados.get("valor"))
    tentativas = _to_int(dados.get("tentativas"))
    tipo_transacao = _normalizar_texto(dados.get("tipo_transacao"))
    pais = _normalizar_texto(dados.get("pais"))
    dispositivo = _normalizar_texto(dados.get("dispositivo"))
    horario = _parse_hora(dados.get("hora"))

    if media_historica > 0 and valor > (media_historica * 3):
        score += 3
        motivos.append(
            f"valor 3x maior que a média histórica (Média: R$ {media_historica:.2f})")

    if frequencia_recente >= 3:
        score += 3
        motivos.append(
            f"alta frequência: {frequencia_recente} transações nos últimos 30 min")

    if pais not in {"", "brasil", "br"}:
        if em_viagem:
            motivos.append(
                "transação internacional (justificada por viagem cadastrada)")
        else:
            score += 2
            motivos.append("transação fora do país esperado")

    if resultado_ml.get("is_anomalia_ml"):
        score += 4
        score_decisao = resultado_ml.get("score_ml", 0)
        motivos.append(
            f"anomalia comportamental detectada por IA (score_ml: {score_decisao:.2f})")

    if valor >= 5000:
        score += 3
        motivos.append("valor muito alto")
    elif valor >= 2000:
        score += 2
        motivos.append("valor alto")

    if horario is not None and time(0, 0, 0) <= horario <= time(5, 0, 0):
        score += 2
        motivos.append("transação em horário de risco")

    if tentativas >= 5:
        score += 3
        motivos.append("muitas tentativas")
    elif tentativas >= 3:
        score += 2
        motivos.append("várias tentativas")

    if tipo_transacao == "pix" and valor >= 2000:
        score += 2
        motivos.append("pix com valor alto")

    if pais not in {"", "brasil", "br"}:
        score += 2
        motivos.append("transação fora do país esperado")

    if dispositivo in {"", "unknown", "desconhecido"}:
        score += 2
        motivos.append("dispositivo não identificado")

    if score >= 6:
        classificacao = "alto"
    elif score >= 4:
        classificacao = "medio"
    else:
        classificacao = "baixo"

    return {
        "score": score,
        "classificacao_risco": classificacao,
        "is_fraude": score >= 4,
        "motivos": motivos,
    }
