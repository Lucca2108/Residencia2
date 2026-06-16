from __future__ import annotations

import mysql.connector
from sqlalchemy import create_engine
from urllib.parse import quote_plus

from app.core.config import get_db_settings


def get_connection():
    config = get_db_settings()
    return mysql.connector.connect(**config)


def get_sqlalchemy_engine():
    config = get_db_settings()
    password = quote_plus(str(config.get("password", "")))
    uri = (
        f"mysql+mysqlconnector://{config['user']}:{password}@"
        f"{config['host']}:{config['port']}/{config['database']}"
    )
    return create_engine(uri)

