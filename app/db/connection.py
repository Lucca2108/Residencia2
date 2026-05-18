from __future__ import annotations

import mysql.connector

from app.core.config import get_db_settings


def get_connection():
    config = get_db_settings()
    return mysql.connector.connect(**config)
