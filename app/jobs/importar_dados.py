"""
Job para importação de dados JSON/CSV para o banco de dados.
Processa em lotes para melhor performance.
"""
from __future__ import annotations

import pandas as pd
import mysql.connector
from pathlib import Path

from app.db.connection import get_connection
from app.core.config import get_db_settings


def importar_json_mysql(json_path: Path | None = None) -> None:
    """
    Importa dados JSON convertendo para CSV e usando LOAD DATA LOCAL INFILE.
    Muito mais rápido que INSERT individual.
    """
    if json_path is None:
        BASE_DIR = Path(__file__).resolve().parents[2]
        json_path = BASE_DIR / "data" / "transacoes_treino_sem_fraude.json"

    csv_path = json_path.parent / "transacoes.csv"

    print(f"[IMPORT] Lendo JSON de {json_path}...")
    df = pd.read_json(json_path)
    
    print(f"[IMPORT] Convertendo para CSV ({len(df)} registros)...")
    df.to_csv(csv_path, index=False)

    config = get_db_settings()
    conn = mysql.connector.connect(**config, allow_local_infile=True)
    cursor = conn.cursor()

    sql = f"""
    LOAD DATA LOCAL INFILE '{csv_path.as_posix()}'
    INTO TABLE transacoes
    FIELDS TERMINATED BY ','
    ENCLOSED BY '"'
    LINES TERMINATED BY '\\n'
    IGNORE 1 ROWS
    """

    try:
        print(f"[IMPORT] Inserindo dados na tabela...")
        cursor.execute(sql)
        conn.commit()
        print(f"[IMPORT] Importação finalizada com sucesso! {df.shape[0]} registros inseridos.")
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    importar_json_mysql()
