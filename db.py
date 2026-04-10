from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv()

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
    print(f"[DB] Tentando conectar em {DB_CONFIG['host']}:{DB_CONFIG['port']} | banco={DB_CONFIG['database']} | usuario={DB_CONFIG['user']}")
    conn = mysql.connector.connect(**DB_CONFIG)
    print("[DB] Conexão com MySQL estabelecida com sucesso.")
    return conn


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
    print("[DB] Entrando em create_table_if_not_exists()")
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(CREATE_TABLE_SQL)
        conn.commit()
        print("[DB] Tabela 'transacoes' verificada/criada com sucesso.")
    finally:
        cursor.close()
        conn.close()
        print("[DB] Conexão encerrada após create_table_if_not_exists().")


def get_total_rows() -> int:
    print("[DB] Entrando em get_total_rows()")
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM transacoes")
        total = cursor.fetchone()[0]
        print(f"[DB] Total de registros na tabela: {total}")
        return int(total)
    finally:
        cursor.close()
        conn.close()
        print("[DB] Conexão encerrada após get_total_rows().")


def table_is_empty() -> bool:
    return get_total_rows() == 0


def read_json_records() -> list[tuple]:
    print(f"[DB] Lendo arquivo JSON em: {JSON_FILE_PATH}")

    if not JSON_FILE_PATH.exists():
        raise FileNotFoundError(f"Arquivo JSON não encontrado em: {JSON_FILE_PATH}")

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

    print(f"[DB] JSON carregado com sucesso. Registros lidos: {len(rows)}")
    return rows


def import_json_if_table_is_empty() -> None:
    print("[DB] Entrando em import_json_if_table_is_empty()")

    if not table_is_empty():
        print("[DB] Tabela já possui dados. Importação não será executada.")
        return

    print("[DB] Tabela vazia. Iniciando importação do JSON...")
    rows = read_json_records()

    if not rows:
        print("[DB] Nenhum registro encontrado no JSON.")
        return

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.executemany(INSERT_IMPORT_SQL, rows)
        conn.commit()
        print(f"[DB] Importação concluída com sucesso. Registros inseridos: {len(rows)}")
    finally:
        cursor.close()
        conn.close()
        print("[DB] Conexão encerrada após import_json_if_table_is_empty().")


def adjust_auto_increment() -> None:
    print("[DB] Entrando em adjust_auto_increment()")
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM transacoes")
        next_id = int(cursor.fetchone()[0] or 1)

        if next_id < 1:
            next_id = 1

        cursor.execute(f"ALTER TABLE transacoes AUTO_INCREMENT = {next_id}")
        conn.commit()
        print(f"[DB] AUTO_INCREMENT ajustado para: {next_id}")
    finally:
        cursor.close()
        conn.close()
        print("[DB] Conexão encerrada após adjust_auto_increment().")


def init_database() -> None:
    try:
        print("[DB] ===== Início da inicialização do banco =====")
        create_table_if_not_exists()
        import_json_if_table_is_empty()
        adjust_auto_increment()
        print("[DB] ===== Inicialização do banco concluída com sucesso =====")
    except Error as exc:
        print(f"[DB] Erro de banco durante init_database: {exc}")
        raise RuntimeError(f"Erro ao inicializar banco de dados: {exc}") from exc
    except Exception as exc:
        print(f"[DB] Erro inesperado durante init_database: {exc}")
        raise RuntimeError(f"Erro inesperado ao inicializar banco de dados: {exc}") from exc