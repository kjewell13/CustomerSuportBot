from db.init_db import init_db
from db.chat_db import SqliteChatRepo

def test_sqlite_repo_writes_and_reads(tmp_path):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)

    repo = SqliteChatRepo(db_path)
    session_id = "s1"

    repo.create_session(session_id)
    repo.add_event(session_id, "session_started", {"source": "test"})
    repo.add_message(session_id, "user", "hello")
    repo.add_message(session_id, "assistant", "hi")

    msgs = repo.get_messages(session_id)
    assert [m.role for m in msgs] == ["user", "assistant"]
    assert msgs[0].content == "hello"
    assert msgs[1].content == "hi"

    