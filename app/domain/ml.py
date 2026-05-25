from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from app.db.connection import get_connection

MODEL_PATH = Path(__file__).resolve().parents[2] / "modelo_iforest.pkl"
_model_missing_warned = False


def _normalize_text_column(df: pd.DataFrame, column: str) -> pd.Series:
    return df[column].fillna("").astype(str).str.strip().str.lower()


def _parse_hora_int(valor: Any) -> int:
    texto = str(valor).strip()
    if "days" in texto:
        texto = texto.split()[-1]

    if ":" in texto:
        partes = texto.split(":")
        if partes and partes[0].isdigit():
            return int(partes[0])

    return 0


def _build_features(df: pd.DataFrame, feature_columns: list[str] | None = None) -> pd.DataFrame:
    df = df.copy()
    df["valor"] = df["valor"].astype(float)
    df["tentativas"] = df["tentativas"].astype(int)
    df["hora"] = df["hora"].apply(_parse_hora_int)

    df["tipo_transacao"] = _normalize_text_column(df, "tipo_transacao")
    df["categoria"] = _normalize_text_column(df, "categoria")
    df["pais"] = _normalize_text_column(df, "pais")
    df["estado"] = _normalize_text_column(df, "estado")
    df["dispositivo"] = _normalize_text_column(df, "dispositivo")

    df["flag_pais_brasil"] = df["pais"].isin({"brasil", "br"}).astype(int)
    df["flag_estado_vazio"] = (df["estado"] == "").astype(int)
    df["flag_dispositivo_desconhecido"] = df["dispositivo"].isin({"", "unknown", "desconhecido"}).astype(int)
    df["flag_is_international"] = (~df["pais"].isin({"brasil", "br", ""})).astype(int)

    cat_columns = ["tipo_transacao", "categoria", "pais", "estado", "dispositivo"]
    df = pd.get_dummies(df, columns=cat_columns, dummy_na=False)

    if feature_columns is not None:
        df = df.reindex(columns=feature_columns, fill_value=0)

    return df


def treinar_modelo_iforest(log: bool = True) -> None:
    if log:
        print("[ML] Iniciando extração de dados para treinamento...")

    conn = get_connection()
    try:
        query = "SELECT valor, hora, tentativas, tipo_transacao, categoria, pais, estado, dispositivo, is_fraude FROM transacoes"
        df = pd.read_sql(query, conn)
    finally:
        conn.close()

    if df.empty:
        if log:
            print("[ML] Sem dados suficientes para treinar o modelo.")
        return

    y = df["is_fraude"].astype(int)
    X = _build_features(df.drop(columns=["is_fraude"]))

    if X.empty or len(y.unique()) < 2:
        if log:
            print("[ML] Dados insuficientes para treinar modelo supervisionado.")
        return

    print(f"[ML] Treinando modelo supervisionado com {len(X)} registros...")
    clf = RandomForestClassifier(
        n_estimators=150,
        class_weight="balanced",
        random_state=42,
        n_jobs=1,
    )
    clf.fit(X, y)

    joblib.dump({"model": clf, "feature_columns": list(X.columns)}, MODEL_PATH)
    if log:
        print(f"[ML] Modelo salvo com sucesso em: {MODEL_PATH}")


def prever_anomalia(dados_transacao: dict[str, Any]) -> dict[str, Any]:
    global _model_missing_warned

    if not MODEL_PATH.exists():
        if not _model_missing_warned:
            print("[ML] Modelo não encontrado. Tentando treinar automaticamente se houver dados suficientes...")
            _model_missing_warned = True

        treinar_modelo_iforest(log=False)
        if not MODEL_PATH.exists():
            return {"is_anomalia_ml": False, "score_ml": 0.0}

    info = joblib.load(MODEL_PATH)
    clf = info["model"]
    feature_columns = info["feature_columns"]

    df_input = pd.DataFrame([
        {
            "valor": float(dados_transacao.get("valor", 0)),
            "hora": str(dados_transacao.get("hora", "00:00:00")),
            "tentativas": int(dados_transacao.get("tentativas", 1)),
            "tipo_transacao": dados_transacao.get("tipo_transacao", ""),
            "categoria": dados_transacao.get("categoria", ""),
            "pais": dados_transacao.get("pais", ""),
            "estado": dados_transacao.get("estado", ""),
            "dispositivo": dados_transacao.get("dispositivo", ""),
        }
    ])

    X_input = _build_features(df_input, feature_columns=feature_columns)
    pred = clf.predict(X_input)[0]
    proba = float(clf.predict_proba(X_input)[0][1]) if hasattr(clf, "predict_proba") else 0.0

    return {
        "is_anomalia_ml": bool(pred == 1),
        "score_ml": proba,
    }
