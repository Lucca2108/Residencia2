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
    resultado_ml = resultado_ml or {}

    score = 0
    motivos: list[str] = []

    resultado_ml = resultado_ml or {}

    valor = _to_float(dados.get("valor"))
    tentativas = _to_int(dados.get("tentativas"))
    tipo_transacao = _normalizar_texto(dados.get("tipo_transacao"))
    categoria = _normalizar_texto(dados.get("categoria"))
    pais = _normalizar_texto(dados.get("pais"))
    dispositivo = _normalizar_texto(dados.get("dispositivo"))
    ip_origem = _normalizar_texto(dados.get("ip_origem"))
    horario = _parse_hora(dados.get("hora"))

    if media_historica > 0:
        if valor > media_historica * 2.5:
            score += 4
            motivos.append(
                f"valor 2.5x maior que a média histórica (Média: R$ {media_historica:.2f})")
        elif valor > media_historica * 1.8:
            score += 3
            motivos.append(
                f"valor 1.8x maior que a média histórica (Média: R$ {media_historica:.2f})")
        elif valor > media_historica * 1.5:
            score += 2
            motivos.append(
                f"valor 1.5x maior que a média histórica (Média: R$ {media_historica:.2f})")
        elif valor > media_historica * 1.2:
            score += 1
            motivos.append(
                f"valor 1.2x maior que a média histórica (Média: R$ {media_historica:.2f})")
    else:
        if valor >= 5000:
            score += 3
            motivos.append("valor muito alto")
        elif valor >= 2000:
            score += 2
            motivos.append("valor alto")

    if frequencia_recente >= 3:
        score += 3
        motivos.append(
            f"alta frequência: {frequencia_recente} transações nos últimos 30 min")

    if pais not in {"", "brasil", "br"}:
        if em_viagem:
            motivos.append(
                "transação internacional (justificada por viagem cadastrada)")
        else:
            score += 3
            motivos.append("transação fora do país esperado")

    if resultado_ml.get("is_anomalia_ml"):
        ml_score = float(resultado_ml.get("score_ml", 0.0))
        score += 3
        if ml_score >= 0.8:
            score += 1
        motivos.append(
            f"anomalia comportamental detectada por IA (score_ml: {ml_score:.2f})")

    if horario is not None and (
        time(0, 0, 0) <= horario <= time(5, 0, 0)
        or time(22, 0, 0) <= horario <= time(23, 59, 59)
    ):
        score += 2
        motivos.append("transação em horário de risco")

    if tentativas >= 5:
        score += 3
        motivos.append("muitas tentativas")
    elif tentativas >= 3:
        score += 2
        motivos.append("várias tentativas")

    if tipo_transacao == "pix" and valor >= 1500:
        score += 3
        motivos.append("pix com valor alto")

    if tipo_transacao == "credito" and valor >= 3000:
        score += 2
        motivos.append("crédito com valor alto")

    if categoria in {"eletronicos", "veiculos", "lazer", "vestuario"} and valor >= 1500:
        score += 2
        motivos.append("categoria de alto risco com valor elevado")

    if pais not in {"", "brasil", "br"}:
        score += 2
        motivos.append("transação fora do país esperado")

    if dispositivo in {"", "unknown", "desconhecido"}:
        score += 2
        motivos.append("dispositivo não identificado")

    if ip_origem in {"", "unknown", "desconhecido"}:
        score += 2
        motivos.append("IP de origem não identificado")

    if score >= 7:
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
