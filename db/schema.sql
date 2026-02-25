CREATE TABLE IF NOT EXISTS chat_sessions (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_messages (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  role TEXT NOT NULL,            -- "user" | "assistant" | "system"
  content TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(session_id) REFERENCES chat_sessions(id)
);

CREATE TABLE IF NOT EXISTS chat_events (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  event_type TEXT NOT NULL,      -- "intent_detected", "tool_called", ...
  payload_json TEXT NOT NULL,    -- JSON string
  created_at TEXT NOT NULL,
  FOREIGN KEY(session_id) REFERENCES chat_sessions(id)
);