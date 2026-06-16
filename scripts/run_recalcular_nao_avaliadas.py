#!/usr/bin/env python
"""
Script para reavaliação de fraude apenas em transações não avaliadas.

Uso:
    python scripts/run_recalcular_nao_avaliadas.py

Este script carrega apenas transações com status_validacao = 'nao_avaliada' e as reavalia usando:
- Regras de negócio (avaliar_fraude)
- Machine Learning (prever_anomalia)
- Histórico de contas e viagens
"""
import sys
from pathlib import Path

# Ensure we're in the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.db.init import evaluate_fraud_for_unevaluated


def main():
    """Executa a reavaliação de fraude."""
    print("[SCRIPT] Iniciando reavaliação de fraude... Somente transações não avaliadas serão processadas.")
    print("[SCRIPT] Isso pode levar alguns minutos dependendo da quantidade de dados.\n")
    
    count = evaluate_fraud_for_unevaluated()
    print(f"\n[SCRIPT] Processo concluído! {count} transações atualizadas.")


if __name__ == "__main__":
    main()
