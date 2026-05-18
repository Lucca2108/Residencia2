from __future__ import annotations

from typing import Any

from app.db.connection import get_connection
from app.utils.normalization import normalize_row


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
        cursor.execute("SELECT * FROM transacoes WHERE id = %s", (transacao_id,))
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
    is_fraude: int | None = None,
    data_inicial: str | None = None,
    data_final: str | None = None,
    valor_min: float | None = None,
    valor_max: float | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    sql = "SELECT * FROM transacoes"
    conditions: list[str] = []
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
        params.append(is_fraude)

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


def get_estatisticas_conta(conta: str) -> float:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT AVG(valor) as media_valor FROM transacoes WHERE conta = %s AND is_fraude = 0",
            (conta,),
        )
        row = cursor.fetchone()
        return float(row["media_valor"]) if row and row["media_valor"] else 0.0
    finally:
        cursor.close()
        conn.close()


def get_frequencia_recente(conta: str, data_tx: str, hora_tx: str, minutos: int = 30) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        sql = """
        SELECT COUNT(*) FROM transacoes
        WHERE conta = %s
        AND TIMESTAMP(data, hora) BETWEEN TIMESTAMP(%s, %s) - INTERVAL %s MINUTE AND TIMESTAMP(%s, %s)
        """
        cursor.execute(sql, (conta, data_tx, hora_tx, minutos, data_tx, hora_tx))
        total = cursor.fetchone()[0]
        return int(total)
    finally:
        cursor.close()
        conn.close()


def create_transacao_record(values: dict[str, Any]) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        sql = """
        INSERT INTO transacoes (
            valor, data, hora, dia_semana, categoria, conta, cidade, estado, pais,
            latitude, longitude, tipo_transacao, dispositivo, estabelecimento,
            tentativas, ip_origem, is_fraude, status_validacao
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values_tuple = (
            values["valor"],
            values["data"],
            values["hora"],
            values["dia_semana"],
            values["categoria"],
            values["conta"],
            values["cidade"],
            values["estado"],
            values["pais"],
            values.get("latitude"),
            values.get("longitude"),
            values["tipo_transacao"],
            values["dispositivo"],
            values["estabelecimento"],
            values["tentativas"],
            values["ip_origem"],
            1 if values["is_fraude"] else 0,
            values["status_validacao"],
        )
        cursor.execute(sql, values_tuple)
        conn.commit()
        return cursor.lastrowid
    finally:
        cursor.close()
        conn.close()


def update_transacao_record(transacao_id: int, values: dict[str, Any]) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
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
            is_fraude = %s,
            status_validacao = %s
        WHERE id = %s
        """
        values_tuple = (
            values["valor"],
            values["data"],
            values["hora"],
            values["dia_semana"],
            values["categoria"],
            values["conta"],
            values["cidade"],
            values["estado"],
            values["pais"],
            values.get("latitude"),
            values.get("longitude"),
            values["tipo_transacao"],
            values["dispositivo"],
            values["estabelecimento"],
            values["tentativas"],
            values["ip_origem"],
            1 if values["is_fraude"] else 0,
            values.get("status_validacao", "aprovada"),
            transacao_id,
        )
        cursor.execute(sql, values_tuple)
        conn.commit()
        return cursor.rowcount > 0
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
