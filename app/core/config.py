from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]
ENV_FILE_PATH = BASE_DIR / ".env"


def load_environment() -> None:
    load_dotenv(dotenv_path=ENV_FILE_PATH, override=True)


def get_db_settings() -> dict[str, Any]:
    load_environment()
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", "1234"),
        "database": os.getenv("DB_NAME", "bancodobrasil"),
        "port": int(os.getenv("DB_PORT", "3306")),
    }
