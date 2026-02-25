import pytest
from models.chat_state import ChatState
import server

@pytest.mark.asyncio
async def test_get_response_strips_and_delegates(monkeypatch):
    async def fake_handle_client_input(text, state):
        assert text == "hello"   # verifies .strip()
        assert isinstance(state, ChatState)
        return "OK"

    monkeypatch.setattr(server.ChatManager, "handle_client_input", fake_handle_client_input)

    state = ChatState()
    out = await server.get_response("  hello  ", state)
    assert out == "OK"