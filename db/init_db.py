import os
import sqlite3
from pathlib import Path

DEFAULT_PATH = "data/app.db"
SCHEMA_PATH = Path(__file__).with_name("schema.sql")

def init_db(db_path: str = DEFAULT_PATH) -> None:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.commit()
    finally:
        conn.close()
    

if __name__ == "__main__":
    init_db(os.getenv("DB_PATH", DEFAULT_PATH))