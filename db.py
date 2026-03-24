import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()


def _build_db_url() -> str:
    user = (os.getenv("IC_DB_USER") or "").strip()
    password = (os.getenv("IC_DB_PASSWORD") or "").strip()
    host = (os.getenv("IC_DB_HOST") or "").strip()
    port = (os.getenv("IC_DB_PORT") or "").strip()
    dbname = (os.getenv("IC_DB_NAME") or "").strip()
    dialect = ("mysql+pymysql").strip()

    if not host:
        raise ValueError("Url ou host nao configurado.")

    return f"{dialect}://{user}:{password}@{host}:{port}/{dbname}"


def get_engine():
    url = _build_db_url()
    return create_engine(url, pool_pre_ping=True)


def load_sql(name: str) -> str:
    path = Path(__file__).parent / "sql" / name
    if path.suffix != ".sql":
        path = path.with_suffix(".sql")
    return path.read_text(encoding="utf-8")


def query_df(
        sql_text: str, params: dict | None = None, engine=None
) -> pd.DataFrame:
    engine = engine or get_engine()
    with engine.connect() as conn:
        return pd.read_sql(text(sql_text), conn, params=params or {})
