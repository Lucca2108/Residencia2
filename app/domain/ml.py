from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier

from app.db.connection import get_connection, get_sqlalchemy_engine

MODEL_DIR = Path(__file__).resolve().parents[2]
MODEL_PATHS = {
    "rf": MODEL_DIR / "modelo_rf.pkl",
    "iforest": MODEL_DIR / "modelo_iforest.pkl",
}
DEFAULT_ALGORITHM = "both"
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


def _get_model_path(algorithm: Literal["rf", "iforest"]) -> Path:
    return MODEL_PATHS[algorithm]


def _save_model(model: Any, feature_columns: list[str] | None, algorithm: Literal["rf", "iforest"]) -> None:
    model_path = _get_model_path(algorithm)
    joblib.dump(
        {
            "model_type": algorithm,
            "model": model,
            "feature_columns": list(feature_columns) if feature_columns is not None else None,
        },
        model_path,
    )


def _load_model(algorithm: Literal["rf", "iforest"]) -> dict[str, Any] | None:
    model_path = _get_model_path(algorithm)
    if not model_path.exists():
        return None

    info = joblib.load(model_path)
    if isinstance(info, dict) and "model" in info:
        return info

    return {"model_type": algorithm, "model": info, "feature_columns": None}


def _prepare_input(dados_transacao: dict[str, Any], feature_columns: list[str] | None) -> pd.DataFrame:
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
    return _build_features(df_input, feature_columns=feature_columns)


def _get_prediction(algorithm: Literal["rf", "iforest"], dados_transacao: dict[str, Any]) -> dict[str, Any]:
    model_path = _get_model_path(algorithm)
    if not model_path.exists():
        if algorithm == "iforest":
            treinar_modelo_iforest(log=False)
        else:
            treinar_modelo_rf(log=False)

    info = _load_model(algorithm)
    if info is None:
        return {"model_type": algorithm, "is_anomalia_ml": False, "score_ml": 0.0}

    clf = info["model"]
    feature_columns = info.get("feature_columns")
    model_type = info.get("model_type", algorithm)

    if model_type == "iforest":
        return _predict_with_isolation_forest(clf, feature_columns, dados_transacao)

    return _predict_with_random_forest(clf, feature_columns, dados_transacao)


def _combine_predictions(rf_result: dict[str, Any], iforest_result: dict[str, Any]) -> dict[str, Any]:
    combined_score = rf_result["score_ml"]
    return {
        "is_anomalia_ml": rf_result["is_anomalia_ml"] or iforest_result["is_anomalia_ml"],
        "score_ml": combined_score,
        "rf": rf_result,
        "iforest": iforest_result,
    }


def treinar_modelo_rf(log: bool = True) -> None:
    if log:
        print("[ML] Iniciando extração de dados para treinamento do RandomForest...")

    engine = get_sqlalchemy_engine()
    query = "SELECT valor, hora, tentativas, tipo_transacao, categoria, pais, estado, dispositivo, is_fraude FROM transacoes"
    df = pd.read_sql(query, engine)

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

    if log:
        print(f"[ML] Treinando RandomForestClassifier com {len(X)} registros...")

    clf = RandomForestClassifier(
        n_estimators=150,
        class_weight="balanced",
        random_state=42,
        n_jobs=1,
    )
    clf.fit(X, y)

    _save_model(clf, list(X.columns), "rf")
    if log:
        print(f"[ML] Modelo RandomForest salvo com sucesso em: {_get_model_path('rf')}")


def treinar_modelo_iforest(log: bool = True) -> None:
    if log:
        print("[ML] Iniciando extração de dados para treinamento do IsolationForest...")

    engine = get_sqlalchemy_engine()
    query = "SELECT valor, hora, tentativas, tipo_transacao, categoria, pais, estado, dispositivo FROM transacoes"
    df = pd.read_sql(query, engine)

    if df.empty:
        if log:
            print("[ML] Sem dados suficientes para treinar o modelo.")
        return

    X = _build_features(df)
    if X.empty:
        if log:
            print("[ML] Dados insuficientes para treinar IsolationForest.")
        return

    if log:
        print(f"[ML] Treinando IsolationForest com {len(X)} registros...")

    clf = IsolationForest(
        n_estimators=100,
        contamination=0.05,
        random_state=42,
    )
    clf.fit(X)

    _save_model(clf, list(X.columns), "iforest")
    if log:
        print(f"[ML] Modelo IsolationForest salvo com sucesso em: {_get_model_path('iforest')}")


def _predict_with_random_forest(clf: RandomForestClassifier, feature_columns: list[str] | None, dados_transacao: dict[str, Any]) -> dict[str, Any]:
    X_input = _prepare_input(dados_transacao, feature_columns)

    pred = clf.predict(X_input)[0]
    proba = float(clf.predict_proba(X_input)[0][1]) if hasattr(clf, "predict_proba") else 0.0

    return {
        "is_anomalia_ml": bool(pred == 1),
        "score_ml": proba,
    }


def _predict_with_isolation_forest(clf: IsolationForest, feature_columns: list[str] | None, dados_transacao: dict[str, Any]) -> dict[str, Any]:
    X_input = _prepare_input(dados_transacao, feature_columns)

    pred = clf.predict(X_input)[0]
    score = float(clf.decision_function(X_input)[0]) if hasattr(clf, "decision_function") else 0.0

    return {
        "is_anomalia_ml": bool(pred == -1),
        "score_ml": score,
    }


def prever_anomalia(
    dados_transacao: dict[str, Any],
    algorithm: Literal["rf", "iforest", "both"] = DEFAULT_ALGORITHM,
) -> dict[str, Any]:
    global _model_missing_warned

    if algorithm == "both":
        rf_result = _get_prediction("rf", dados_transacao)
        iforest_result = _get_prediction("iforest", dados_transacao)
        return _combine_predictions(rf_result, iforest_result)

    model_path = _get_model_path(algorithm)
    if not model_path.exists():
        if not _model_missing_warned:
            print("[ML] Modelo não encontrado. Tentando treinar automaticamente se houver dados suficientes...")
            _model_missing_warned = True

        if algorithm == "iforest":
            treinar_modelo_iforest(log=False)
        else:
            treinar_modelo_rf(log=False)

        if not model_path.exists():
            return {"is_anomalia_ml": False, "score_ml": 0.0}

    info = _load_model(algorithm)
    if info is None:
        return {"is_anomalia_ml": False, "score_ml": 0.0}

    clf = info["model"]
    feature_columns = info.get("feature_columns")
    model_type = info.get("model_type", algorithm)

    if model_type == "iforest":
        return _predict_with_isolation_forest(clf, feature_columns, dados_transacao)

    return _predict_with_random_forest(clf, feature_columns, dados_transacao)
