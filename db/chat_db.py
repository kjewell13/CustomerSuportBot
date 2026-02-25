import json
import os
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

DEFAULT_DB_PATH = "data/app.db"

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

@dataclass(frozen=True)
class ChatMessageRow:
    session_id: str
    role: str
    content: str
    created_at: str

class SqliteChatRepo:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.getenv("DB_PATH", DEFAULT_DB_PATH)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def create_session(self, session_id: str, created_at: Optional[str] = None) -> None:
        created_at = created_at or now_iso()
        with self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO chat_sessions (id, created_at) VALUES (?, ?)",
                (session_id, created_at),
            )
            conn.commit()

    def add_message(self, session_id: str, role: str, content: str, created_at: Optional[str] = None) -> None:
        created_at = created_at or now_iso()
        msg_id = str(uuid.uuid4())
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO chat_messages (id, session_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
                (msg_id, session_id, role, content, created_at),
            )
            conn.commit()

    def add_event(self, session_id: str, event_type: str, payload: Dict[str, Any], created_at: Optional[str] = None) -> None:
        created_at = created_at or now_iso()
        event_id = str(uuid.uuid4())
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO chat_events (id, session_id, event_type, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
                (event_id, session_id, event_type, json.dumps(payload), created_at),
            )
            conn.commit()

    def get_messages(self, session_id: str) -> List[ChatMessageRow]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT session_id, role, content, created_at FROM chat_messages WHERE session_id=? ORDER BY created_at ASC",
                (session_id,),
            ).fetchall()
            return [ChatMessageRow(**dict(r)) for r in rows]