from __future__ import annotations

import os
from typing import Any

import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest

from db import get_connection

MODEL_PATH = "modelo_iforest.pkl"


def treinar_modelo_iforest() -> None:
    """Busca o histórico no banco de dados e treina o modelo de anomalia."""
    print("[ML] Iniciando extração de dados para treinamento...")
    conn = get_connection()
    try:
        query = "SELECT valor, hora, tentativas FROM transacoes"
        df = pd.read_sql(query, conn)
    finally:
        conn.close()

    if df.empty:
        print("[ML] Sem dados suficientes para treinar o modelo.")
        return

    df['hora'] = df['hora'].astype(str).str.slice(0, 2).astype(int)

    features = df[['valor', 'hora', 'tentativas']]

    print(f"[ML] Treinando Isolation Forest com {len(features)} registros...")
    clf = IsolationForest(
        n_estimators=100, contamination=0.05, random_state=42)
    clf.fit(features)

    joblib.dump(clf, MODEL_PATH)
    print(f"[ML] Modelo salvo com sucesso em: {MODEL_PATH}")


def prever_anomalia(dados_transacao: dict[str, Any]) -> dict[str, Any]:
    """Recebe os dados de uma nova transação e devolve a previsão do ML."""
    if not os.path.exists(MODEL_PATH):
        print(
            "[ML] Modelo não encontrado. Considere rodar treinar_modelo_iforest() primeiro.")
        return {"is_anomalia_ml": False, "score_ml": 0.0}

    clf = joblib.load(MODEL_PATH)

    hora_str = str(dados_transacao.get("hora", "00:00:00"))
    hora_int = int(hora_str.split(":")[0]) if ":" in hora_str else 0

    df_input = pd.DataFrame([{
        'valor': float(dados_transacao.get('valor', 0)),
        'hora': hora_int,
        'tentativas': int(dados_transacao.get('tentativas', 1))
    }])

    pred = clf.predict(df_input)[0]
    decision_score = clf.decision_function(df_input)[0]
    return {
        "is_anomalia_ml": bool(pred == -1),
        "score_ml": float(decision_score)
    }
