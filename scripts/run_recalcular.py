#!/usr/bin/env python
"""
Script para reavaliação de fraude em todas as transações.

Uso:
    python scripts/run_recalcular.py

Este script carrega TODAS as transações e as reavalia usando:
- Regras de negócio (avaliar_fraude)
- Machine Learning (prever_anomalia)
- Histórico de contas e viagens
"""
import sys
from pathlib import Path

# Ensure we're in the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.jobs.recalcular_fraude import recalcular_todas_transacoes


def main():
    """Executa a reavaliação de fraude."""
    print("[SCRIPT] Iniciando reavaliação de fraude...")
    print("[SCRIPT] Isso pode levar alguns minutos dependendo da quantidade de dados.\n")
    
    count = recalcular_todas_transacoes()
    print(f"\n[SCRIPT] Processo concluído! {count} transações atualizadas.")


if __name__ == "__main__":
    main()
