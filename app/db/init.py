from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from mysql.connector import Error

from app.db.connection import get_connection
from app.domain.fraude import avaliar_fraude
from app.domain.ml import prever_anomalia
from app.repositories.transacao_repository import (
    get_estatisticas_conta,
    get_frequencia_recente,
)
from app.repositories.viagem_repository import get_viagem_ativa_por_conta
from app.schemas import TransacaoCreate

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
JSON_FILE_PATH = DATA_DIR / "transacoes_treino.json"
ENV_FILE_PATH = BASE_DIR / ".env"


CREATE_TABLE_TRANSACOES_SQL = """
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
    status_validacao VARCHAR(50) DEFAULT 'aprovada',
    PRIMARY KEY (id)
)
"""

CREATE_TABLE_VIAGENS_SQL = """
CREATE TABLE IF NOT EXISTS viagens (
    id INT NOT NULL AUTO_INCREMENT,
    conta VARCHAR(100) NOT NULL,
    cidade_destino VARCHAR(100) NOT NULL,
    estado_destino VARCHAR(100),
    pais_destino VARCHAR(100) NOT NULL,
    data_inicio DATE NOT NULL,
    data_fim DATE NOT NULL,
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
    is_fraude,
    status_validacao
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


def load_environment() -> None:
    load_dotenv(dotenv_path=ENV_FILE_PATH, override=True)


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


def create_table_if_not_exists() -> None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(CREATE_TABLE_TRANSACOES_SQL)
        cursor.execute(CREATE_TABLE_VIAGENS_SQL)
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


def read_json_records() -> list[dict[str, Any]]:
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

    return items


def import_json_if_table_is_empty() -> None:
    if not table_is_empty():
        return

    items = read_json_records()
    if not items:
        return

    conn = get_connection()
    cursor = conn.cursor()
    try:
        for item in items:
            payload = TransacaoCreate(
                valor=float(item["valor"]),
                data=normalize_date_string(item["data"]),
                hora=normalize_time_string(item["hora"]),
                dia_semana=str(item["dia_semana"]),
                categoria=str(item["categoria"]),
                conta=str(item["conta"]),
                cidade=str(item["cidade"]),
                estado=item.get("estado"),
                pais=str(item["pais"]),
                latitude=normalize_nullable_float(item.get("latitude")),
                longitude=normalize_nullable_float(item.get("longitude")),
                tipo_transacao=str(item["tipo_transacao"]),
                dispositivo=str(item["dispositivo"]),
                estabelecimento=str(item["estabelecimento"]),
                tentativas=int(item["tentativas"]),
                ip_origem=str(item["ip_origem"]),
            )

            media_hist = get_estatisticas_conta(payload.conta)
            freq = get_frequencia_recente(payload.conta, payload.data, normalize_time_string(item["hora"]))
            em_viagem_legitima = _transacao_em_viagem_legitima(payload.conta, payload.pais, payload.estado, payload.data)
            resultado_ia = prever_anomalia(payload.model_dump())
            analise_fraude = avaliar_fraude(
                payload,
                media_historica=media_hist,
                frequencia_recente=freq,
                em_viagem=em_viagem_legitima,
                resultado_ml=resultado_ia,
            )

            status_validacao = "pendente" if analise_fraude["is_fraude"] else "aprovada"
            cursor.execute(
                INSERT_IMPORT_SQL,
                (
                    int(item["id"]),
                    float(item["valor"]),
                    normalize_date_string(item["data"]),
                    normalize_time_string(item["hora"]),
                    str(item["dia_semana"]),
                    str(item["categoria"]),
                    str(item["conta"]),
                    str(item["cidade"]),
                    item.get("estado"),
                    str(item["pais"]),
                    normalize_nullable_float(item.get("latitude")),
                    normalize_nullable_float(item.get("longitude")),
                    str(item["tipo_transacao"]),
                    str(item["dispositivo"]),
                    str(item["estabelecimento"]),
                    int(item["tentativas"]),
                    str(item["ip_origem"]),
                    1 if analise_fraude["is_fraude"] else 0,
                    status_validacao,
                ),
            )

        conn.commit()
    finally:
        cursor.close()
        conn.close()


def _atualizar_is_fraude_transacao(transacao_id: int, is_fraude: bool, status_validacao: str) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE transacoes SET is_fraude = %s, status_validacao = %s WHERE id = %s",
            (1 if is_fraude else 0, status_validacao, transacao_id),
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def recalcular_fraude_existente() -> None:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT * FROM transacoes WHERE status_validacao IN ('aprovada','pendente') ORDER BY id"
        )
        rows = cursor.fetchall() or []
    finally:
        cursor.close()
        conn.close()

    for row in rows:
        media_hist = get_estatisticas_conta(row["conta"])
        freq = get_frequencia_recente(row["conta"], str(row["data"]), str(row["hora"]))
        em_viagem_legitima = _transacao_em_viagem_legitima(row["conta"], row["pais"], row.get("estado"), str(row["data"]))
        resultado_ia = prever_anomalia(row)
        analise_fraude = avaliar_fraude(
            row,
            media_historica=media_hist,
            frequencia_recente=freq,
            em_viagem=em_viagem_legitima,
            resultado_ml=resultado_ia,
        )
        status_validacao = "pendente" if analise_fraude["is_fraude"] else "aprovada"
        _atualizar_is_fraude_transacao(row["id"], analise_fraude["is_fraude"], status_validacao)


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
        load_environment()
        create_table_if_not_exists()
    except Error as exc:
        raise RuntimeError(f"Erro ao inicializar banco de dados: {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"Erro inesperado ao inicializar banco de dados: {exc}") from exc
