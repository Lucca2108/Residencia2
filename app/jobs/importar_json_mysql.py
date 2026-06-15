"""
Job para importação de dados JSON/CSV para o banco de dados.
Processa em lotes para melhor performance.
"""
from __future__ import annotations

import pandas as pd
import mysql.connector
from pathlib import Path

from app.core.config import get_db_settings


def importar_json_mysql(json_path: Path | None = None) -> None:
    """
    Importa dados JSON para o banco usando inserções em lote.
    Esse método não depende de LOAD DATA LOCAL INFILE.
    """
    if json_path is None:
        BASE_DIR = Path(__file__).resolve().parents[2]
        json_path = BASE_DIR / "data" / "transacoes_treino_sem_fraude.json"

    print(f"[IMPORT] Lendo JSON de {json_path}...")
    df = pd.read_json(json_path)


    config = get_db_settings()
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor()

    insert_sql = """
    INSERT INTO transacoes (
        id, valor, data, hora, dia_semana, categoria, conta, cidade, estado,
        pais, latitude, longitude, tipo_transacao, dispositivo, estabelecimento,
        tentativas, ip_origem, is_fraude
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    valores = [
        (
            int(row.id),
            float(row.valor),
            str(row.data),
            str(row.hora),
            str(row.dia_semana),
            str(row.categoria),
            str(row.conta),
            str(row.cidade),
            str(row.estado),
            str(row.pais),
            None if pd.isna(row.latitude) else float(row.latitude),
            None if pd.isna(row.longitude) else float(row.longitude),
            str(row.tipo_transacao),
            str(row.dispositivo),
            str(row.estabelecimento),
            int(row.tentativas),
            str(row.ip_origem),
            int(row.is_fraude),
        )
        for row in df.itertuples(index=False)
    ]

    batch_size = 1000
    total = len(valores)
    print(f"[IMPORT] Inserindo {total} registros em lotes de {batch_size}...")

    try:
        for i in range(0, total, batch_size):
            lote = valores[i : i + batch_size]
            cursor.executemany(insert_sql, lote)
            conn.commit()
            print(f"[IMPORT] Lote {i // batch_size + 1} de {((total - 1) // batch_size) + 1} inserido com sucesso!")

        print(f"[IMPORT] Importação finalizada com sucesso! {total} registros inseridos.")
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    importar_json_mysql()
