from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any


def normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    if value is None:
        return False

    if isinstance(value, (int, float)):
        return bool(value)

    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "t", "yes", "y", "sim"}

    return False


def normalize_date(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date().isoformat()

    if isinstance(value, date):
        return value.isoformat()

    return str(value)[:10]


def normalize_time(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, time):
        return value.strftime("%H:%M:%S")

    if isinstance(value, timedelta):
        total_seconds = int(value.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02}:{minutes:02}:{seconds:02}"

    text = str(value).strip()
    if len(text) == 5:
        return f"{text}:00"

    return text


def normalize_decimal(value: Any):
    if value is None:
        return None

    if isinstance(value, Decimal):
        return float(value)

    return value


def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "valor": float(normalize_decimal(row["valor"])),
        "data": normalize_date(row["data"]),
        "hora": normalize_time(row["hora"]),
        "dia_semana": row["dia_semana"],
        "categoria": row["categoria"],
        "conta": row["conta"],
        "cidade": row["cidade"],
        "estado": row["estado"],
        "pais": row["pais"],
        "latitude": None if row["latitude"] is None else float(normalize_decimal(row["latitude"])),
        "longitude": None if row["longitude"] is None else float(normalize_decimal(row["longitude"])),
        "tipo_transacao": row["tipo_transacao"],
        "dispositivo": row["dispositivo"],
        "estabelecimento": row["estabelecimento"],
        "tentativas": int(row["tentativas"]),
        "ip_origem": row["ip_origem"],
        "is_fraude": normalize_bool(row["is_fraude"]),
    }
