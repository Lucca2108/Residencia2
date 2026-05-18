from __future__ import annotations

from typing import Any

from app.db.connection import get_connection


def create_viagem_record(values: dict[str, Any]) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        sql = """
        INSERT INTO viagens (conta, cidade_destino, estado_destino, pais_destino, data_inicio, data_fim)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        values_tuple = (
            values["conta"],
            values["cidade_destino"],
            values.get("estado_destino"),
            values["pais_destino"],
            values["data_inicio"],
            values["data_fim"],
        )
        cursor.execute(sql, values_tuple)
        conn.commit()
        return cursor.lastrowid
    finally:
        cursor.close()
        conn.close()


def get_viagem_ativa_por_conta(conta: str, data_transacao: str) -> list[dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        sql = """
        SELECT * FROM viagens
        WHERE conta = %s AND %s BETWEEN data_inicio AND data_fim
        """
        cursor.execute(sql, (conta, data_transacao))
        viagens = cursor.fetchall()
        for viagem in viagens:
            if viagem.get("data_inicio"):
                viagem["data_inicio"] = str(viagem["data_inicio"])
            if viagem.get("data_fim"):
                viagem["data_fim"] = str(viagem["data_fim"])
        return viagens
    finally:
        cursor.close()
        conn.close()


def get_viagens_por_conta(conta: str) -> list[dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        sql = "SELECT * FROM viagens WHERE conta = %s ORDER BY data_inicio DESC"
        cursor.execute(sql, (conta,))
        viagens = cursor.fetchall()
        for viagem in viagens:
            if viagem.get("data_inicio"):
                viagem["data_inicio"] = str(viagem["data_inicio"])
            if viagem.get("data_fim"):
                viagem["data_fim"] = str(viagem["data_fim"])
        return viagens
    finally:
        cursor.close()
        conn.close()
