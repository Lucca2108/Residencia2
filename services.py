from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from db import get_connection
from regras_fraude import avaliar_fraude
from schemas import TransacaoCreate, TransacaoUpdate


def normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    if value is None:
        return False

    if isinstance(value, (int, float)):
        return bool(value)

    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "t", "yes", "y", "sim"}

    return False


def normalize_date(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date().isoformat()

    if isinstance(value, date):
        return value.isoformat()

    return str(value)[:10]


def normalize_time(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, time):
        return value.strftime("%H:%M:%S")

    if isinstance(value, timedelta):
        total_seconds = int(value.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02}:{minutes:02}:{seconds:02}"

    text = str(value).strip()
    if len(text) == 5:
        return f"{text}:00"

    return text


def normalize_decimal(value: Any):
    if value is None:
        return None

    if isinstance(value, Decimal):
        return float(value)

    return value


def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "valor": float(normalize_decimal(row["valor"])),
        "data": normalize_date(row["data"]),
        "hora": normalize_time(row["hora"]),
        "dia_semana": row["dia_semana"],
        "categoria": row["categoria"],
        "conta": row["conta"],
        "cidade": row["cidade"],
        "estado": row["estado"],
        "pais": row["pais"],
        "latitude": None if row["latitude"] is None else float(normalize_decimal(row["latitude"])),
        "longitude": None if row["longitude"] is None else float(normalize_decimal(row["longitude"])),
        "tipo_transacao": row["tipo_transacao"],
        "dispositivo": row["dispositivo"],
        "estabelecimento": row["estabelecimento"],
        "tentativas": int(row["tentativas"]),
        "ip_origem": row["ip_origem"],
        "is_fraude": normalize_bool(row["is_fraude"]),
    }


def list_transacoes(limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT * FROM transacoes ORDER BY id LIMIT %s OFFSET %s",
            (limit, offset),
        )
        rows = cursor.fetchall()
        return [normalize_row(row) for row in rows]
    finally:
        cursor.close()
        conn.close()


def get_transacao_by_id(transacao_id: int) -> dict[str, Any] | None:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT * FROM transacoes WHERE id = %s",
            (transacao_id,),
        )
        row = cursor.fetchone()
        return normalize_row(row) if row else None
    finally:
        cursor.close()
        conn.close()


def search_transacoes(
    categoria: str | None = None,
    conta: str | None = None,
    cidade: str | None = None,
    estado: str | None = None,
    pais: str | None = None,
    tipo_transacao: str | None = None,
    dispositivo: str | None = None,
    estabelecimento: str | None = None,
    is_fraude: bool | None = None,
    data_inicial: str | None = None,
    data_final: str | None = None,
    valor_min: float | None = None,
    valor_max: float | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    sql = "SELECT * FROM transacoes"
    conditions = []
    params: list[Any] = []

    if categoria:
        conditions.append("categoria LIKE %s")
        params.append(f"%{categoria}%")

    if conta:
        conditions.append("conta LIKE %s")
        params.append(f"%{conta}%")

    if cidade:
        conditions.append("cidade LIKE %s")
        params.append(f"%{cidade}%")

    if estado:
        conditions.append("estado = %s")
        params.append(estado)

    if pais:
        conditions.append("pais = %s")
        params.append(pais)

    if tipo_transacao:
        conditions.append("tipo_transacao = %s")
        params.append(tipo_transacao)

    if dispositivo:
        conditions.append("dispositivo LIKE %s")
        params.append(f"%{dispositivo}%")

    if estabelecimento:
        conditions.append("estabelecimento LIKE %s")
        params.append(f"%{estabelecimento}%")

    if is_fraude is not None:
        conditions.append("is_fraude = %s")
        params.append(1 if is_fraude else 0)

    if data_inicial:
        conditions.append("data >= %s")
        params.append(data_inicial)

    if data_final:
        conditions.append("data <= %s")
        params.append(data_final)

    if valor_min is not None:
        conditions.append("valor >= %s")
        params.append(valor_min)

    if valor_max is not None:
        conditions.append("valor <= %s")
        params.append(valor_max)

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    sql += " ORDER BY id LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        return [normalize_row(row) for row in rows]
    finally:
        cursor.close()
        conn.close()


def _format_payload_hora(hora: str) -> str:
    return hora if len(hora) == 8 else f"{hora}:00"


def create_transacao(payload: TransacaoCreate) -> dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        analise_fraude = avaliar_fraude(payload)

        sql = """
        INSERT INTO transacoes (
            valor,
            data,
            hora,
            dia_semana,
            categoria,
            conta,
            cidade,
            estado,
            pais,
            latitude,
            longitude,
            tipo_transacao,
            dispositivo,
            estabelecimento,
            tentativas,
            ip_origem,
            is_fraude
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            payload.valor,
            payload.data,
            _format_payload_hora(payload.hora),
            payload.dia_semana,
            payload.categoria,
            payload.conta,
            payload.cidade,
            payload.estado,
            payload.pais,
            payload.latitude,
            payload.longitude,
            payload.tipo_transacao,
            payload.dispositivo,
            payload.estabelecimento,
            payload.tentativas,
            payload.ip_origem,
            1 if analise_fraude["is_fraude"] else 0,
        )

        cursor.execute(sql, values)
        conn.commit()
        transacao_id = cursor.lastrowid
        return get_transacao_by_id(transacao_id)
    finally:
        cursor.close()
        conn.close()


def update_transacao(transacao_id: int, payload: TransacaoUpdate) -> dict[str, Any] | None:
    existing = get_transacao_by_id(transacao_id)
    if not existing:
        return None

    conn = get_connection()
    cursor = conn.cursor()
    try:
        analise_fraude = avaliar_fraude(payload)

        sql = """
        UPDATE transacoes
        SET
            valor = %s,
            data = %s,
            hora = %s,
            dia_semana = %s,
            categoria = %s,
            conta = %s,
            cidade = %s,
            estado = %s,
            pais = %s,
            latitude = %s,
            longitude = %s,
            tipo_transacao = %s,
            dispositivo = %s,
            estabelecimento = %s,
            tentativas = %s,
            ip_origem = %s,
            is_fraude = %s
        WHERE id = %s
        """

        values = (
            payload.valor,
            payload.data,
            _format_payload_hora(payload.hora),
            payload.dia_semana,
            payload.categoria,
            payload.conta,
            payload.cidade,
            payload.estado,
            payload.pais,
            payload.latitude,
            payload.longitude,
            payload.tipo_transacao,
            payload.dispositivo,
            payload.estabelecimento,
            payload.tentativas,
            payload.ip_origem,
            1 if analise_fraude["is_fraude"] else 0,
            transacao_id,
        )

        cursor.execute(sql, values)
        conn.commit()
        return get_transacao_by_id(transacao_id)
    finally:
        cursor.close()
        conn.close()


def delete_transacao(transacao_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM transacoes WHERE id = %s", (transacao_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        cursor.close()
        conn.close()