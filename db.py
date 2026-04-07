from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import mysql.connector
from mysql.connector import Error

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
JSON_FILE_PATH = DATA_DIR / "transacoes_treino.json"

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "Test"),
    "password": os.getenv("DB_PASSWORD", "123456"),
    "database": os.getenv("DB_NAME", "bancodobrasil"),
    "port": int(os.getenv("DB_PORT", "3306")),
}

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS transacoes (
    id INT NOT NULL AUTO_INCREMENT,
    valor DECIMAL(15, 2) NOT NULL,
    data DATE NOT NULL,
    hora TIME NOT NULL,
    dia_semana VARCHAR(20) NOT NULL,
    categoria VARCHAR(100) NOT NULL,
    conta VARCHAR(100) NOT NULL,
    cidade VARCHAR(100) NOT NULL,
    estado VARCHAR(100) NOT NULL,
    pais VARCHAR(100) NOT NULL,
    latitude DECIMAL(10, 6) NULL,
    longitude DECIMAL(10, 6) NULL,
    tipo_transacao VARCHAR(50) NOT NULL,
    dispositivo VARCHAR(100) NOT NULL,
    estabelecimento VARCHAR(255) NOT NULL,
    tentativas INT NOT NULL DEFAULT 1,
    ip_origem VARCHAR(45) NOT NULL,
    is_fraude BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (id)
)
"""

INSERT_IMPORT_SQL = """
INSERT INTO transacoes (
    id,
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
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


def normalize_bool(value: Any) -> int:
    if isinstance(value, bool):
        return 1 if value else 0

    if value is None:
        return 0

    if isinstance(value, (int, float)):
        return 1 if value else 0

    if isinstance(value, str):
        return 1 if value.strip().lower() in {"1", "true", "t", "yes", "y", "sim"} else 0

    return 0


def normalize_date_string(value: Any) -> str:
    if value is None:
        raise ValueError("Campo 'data' não pode ser nulo.")
    return str(value)[:10]


def normalize_time_string(value: Any) -> str:
    if value is None:
        raise ValueError("Campo 'hora' não pode ser nulo.")

    text = str(value).strip()

    if len(text) == 5:
        return f"{text}:00"

    return text


def normalize_nullable_float(value: Any):
    if value in ("", None):
        return None
    return float(value)


def create_table_if_not_exists() -> None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(CREATE_TABLE_SQL)
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def get_total_rows() -> int:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM transacoes")
        total = cursor.fetchone()[0]
        return int(total)
    finally:
        cursor.close()
        conn.close()


def table_is_empty() -> bool:
    return get_total_rows() == 0


def read_json_records() -> list[tuple]:
    if not JSON_FILE_PATH.exists():
        raise FileNotFoundError(
            f"Arquivo JSON não encontrado em: {JSON_FILE_PATH}"
        )

    with JSON_FILE_PATH.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict) and isinstance(payload.get("transacoes"), list):
        items = payload["transacoes"]
    else:
        raise ValueError("Formato de JSON inválido. Esperado: lista de objetos.")

    rows = []
    for item in items:
        rows.append(
            (
                int(item["id"]),
                float(item["valor"]),
                normalize_date_string(item["data"]),
                normalize_time_string(item["hora"]),
                str(item["dia_semana"]),
                str(item["categoria"]),
                str(item["conta"]),
                str(item["cidade"]),
                str(item["estado"]),
                str(item["pais"]),
                normalize_nullable_float(item.get("latitude")),
                normalize_nullable_float(item.get("longitude")),
                str(item["tipo_transacao"]),
                str(item["dispositivo"]),
                str(item["estabelecimento"]),
                int(item["tentativas"]),
                str(item["ip_origem"]),
                normalize_bool(item["is_fraude"]),
            )
        )

    return rows


def import_json_if_table_is_empty() -> None:
    if not table_is_empty():
        return

    rows = read_json_records()
    if not rows:
        return

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.executemany(INSERT_IMPORT_SQL, rows)
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def adjust_auto_increment() -> None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM transacoes")
        next_id = int(cursor.fetchone()[0] or 1)

        if next_id < 1:
            next_id = 1

        cursor.execute(f"ALTER TABLE transacoes AUTO_INCREMENT = {next_id}")
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def init_database() -> None:
    try:
        create_table_if_not_exists()
        import_json_if_table_is_empty()
        adjust_auto_increment()
    except Error as exc:
        raise RuntimeError(f"Erro ao inicializar banco de dados: {exc}") from exc