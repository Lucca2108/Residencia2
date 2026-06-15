#!/usr/bin/env python
"""
Script para importação de dados JSON/CSV para o banco de dados.

Uso:
    python scripts/run_import.py

Este script:
1. Lê o arquivo JSON (data/transacoes_treino_sem_fraude.json)
2. Converte para CSV
3. Usa LOAD DATA LOCAL INFILE para importação rápida
"""
import sys
from pathlib import Path

# Ensure we're in the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.jobs.importar_json_mysql import importar_json_mysql


def main():
    """Executa a importação de dados."""
    print("[SCRIPT] Iniciando importação de dados...")
    print("[SCRIPT] Isso pode levar alguns minutos dependendo da quantidade de dados.\n")
    
    importar_json_mysql()


if __name__ == "__main__":
    main()
