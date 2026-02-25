import json
import pytest

import llm_router
from models.intent import Intent


# -------------------------
# Small helpers / fakes
# -------------------------

class FakeFunction:
    def __init__(self, name: str, arguments: str):
        self.name = name
        self.arguments = arguments

class FakeToolCall:
    def __init__(self, tool_id: str, name: str, args: dict):
        self.id = tool_id
        self.function = FakeFunction(name=name, arguments=json.dumps(args))

class FakeMessage:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []

class FakeChoice:
    def __init__(self, message):
        self.message = message

class FakeResponse:
    def __init__(self, message):
        self.choices = [FakeChoice(message)]


class FakeChatCompletions:
    """
    This object will simulate:
      await client.chat.completions.create(...)
    by returning pre-seeded responses in order.
    """
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []  # keep a log of create() inputs for assertions

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._responses.pop(0)


class FakeClient:
    def __init__(self, responses):
        self.chat = type("chat", (), {})()
        self.chat.completions = FakeChatCompletions(responses)


class DummyState:
    def __init__(self, current_intent=None, pending_data=None, user_data=None):
        self.current_intent = current_intent
        self.pending_data = pending_data
        self.user_data = user_data or {}


# -------------------------
# Tests for get_intent
# -------------------------

@pytest.mark.asyncio
async def test_get_intent_returns_unknown_when_no_tool_calls(monkeypatch):
    fake_client = FakeClient([
        FakeResponse(FakeMessage(content="hi", tool_calls=[]))
    ])
    monkeypatch.setattr(llm_router, "client", fake_client)

    state = DummyState(current_intent=None, pending_data=None, user_data={})
    result = await llm_router.get_intent("hello", state)

    assert result.intent == Intent.UNKNOWN
    assert result.confidence == 0.0
    assert result.next_action == "respond"


@pytest.mark.asyncio
async def test_get_intent_parses_tool_call_into_route_result(monkeypatch):
    tool_call = FakeToolCall(
        tool_id="call_1",
        name="route",
        args={
            "intent": Intent.GREETING.value,
            "confidence": 0.9,
            "next_action": "respond",
            "slot_to_request": None,
            "tool_name": None,
            "tool_args": None,
        },
    )
    fake_client = FakeClient([
        FakeResponse(FakeMessage(content=None, tool_calls=[tool_call]))
    ])
    monkeypatch.setattr(llm_router, "client", fake_client)

    state = DummyState(current_intent=None, pending_data=None, user_data={})
    result = await llm_router.get_intent("hello", state)

    assert result.intent == Intent.GREETING
    assert result.confidence == 0.9
    assert result.next_action == "respond"
    assert result.slot_to_request is None


# -------------------------
# Tests for generate_result
# -------------------------

@pytest.mark.asyncio
async def test_generate_result_returns_direct_response_when_no_tool_calls(monkeypatch):
    fake_client = FakeClient([
        FakeResponse(FakeMessage(content="Here is my answer.", tool_calls=[]))
    ])
    monkeypatch.setattr(llm_router, "client", fake_client)

    state = DummyState(current_intent=Intent.KNOWLEDGE_QA, pending_data=None, user_data={})
    res = await llm_router.generate_result("What is your return policy?", state)

    assert res.next_action == "respond"
    assert res.response_text == "Here is my answer."


@pytest.mark.asyncio
async def test_generate_result_calls_get_order_and_uses_second_model_call(monkeypatch):
    # 1st call returns tool call get_order
    tool_call = FakeToolCall("call_1", "get_order", {"order_id": "124"})
    # 2nd call returns final message after tool output is appended
    fake_client = FakeClient([
        FakeResponse(FakeMessage(content=None, tool_calls=[tool_call])),
        FakeResponse(FakeMessage(content="Your order 124 is Shipped.", tool_calls=[])),
    ])
    monkeypatch.setattr(llm_router, "client", fake_client)

    # Make get_order deterministic (it already is), but we can assert it was used by checking tool output in messages
    state = DummyState(current_intent=Intent.GET_ORDER_INFORMATION, pending_data=None, user_data={"order_id": "124"})
    res = await llm_router.generate_result("Where is my order?", state)

    assert res.response_text == "Your order 124 is Shipped."

    # Assert that the second call included a tool message with the tool output
    second_call_kwargs = fake_client.chat.completions.calls[1]
    msgs = second_call_kwargs["messages"]
    tool_msgs = [m for m in msgs if m["role"] == "tool"]
    assert len(tool_msgs) == 1
    tool_content = json.loads(tool_msgs[0]["content"])
    assert tool_content["status"] == "Shipped"


@pytest.mark.asyncio
async def test_generate_result_calls_knowledge_search(monkeypatch):
    # Patch knowledge_search so we don't rely on filesystem
    def fake_ks(query: str, top_k: int = 3, folder: str = "knowledge"):
        return {"query": query, "top_k": top_k, "matches": [{"source": "x.md", "content": "Return within 30 days."}]}

    monkeypatch.setattr(llm_router, "knowledge_search", fake_ks)

    tool_call = FakeToolCall("call_1", "knowledge_search", {"query": "return policy", "top_k": 2})
    fake_client = FakeClient([
        FakeResponse(FakeMessage(content=None, tool_calls=[tool_call])),
        FakeResponse(FakeMessage(content="We accept returns within 30 days.", tool_calls=[])),
    ])
    monkeypatch.setattr(llm_router, "client", fake_client)

    state = DummyState(current_intent=Intent.KNOWLEDGE_QA, pending_data=None, user_data={})
    res = await llm_router.generate_result("What's your return policy?", state)

    assert "30 days" in res.response_text

    # Verify the tool output made it into the second call messages
    second_msgs = fake_client.chat.completions.calls[1]["messages"]
    tool_msg = next(m for m in second_msgs if m["role"] == "tool")
    payload = json.loads(tool_msg["content"])
    assert payload["top_k"] == 2
    assert payload["matches"][0]["source"] == "x.md"


@pytest.mark.asyncio
async def test_generate_result_unknown_tool_name(monkeypatch):
    tool_call = FakeToolCall("call_1", "weird_tool", {"x": 1})
    fake_client = FakeClient([
        FakeResponse(FakeMessage(content=None, tool_calls=[tool_call])),
        FakeResponse(FakeMessage(content="I can't do that.", tool_calls=[])),
    ])
    monkeypatch.setattr(llm_router, "client", fake_client)

    state = DummyState(current_intent=Intent.UNKNOWN, pending_data=None, user_data={})
    res = await llm_router.generate_result("do something", state)

    assert res.response_text == "I can't do that."

    # Ensure our error object was appended as tool output
    msgs = fake_client.chat.completions.calls[1]["messages"]
    tool_msg = next(m for m in msgs if m["role"] == "tool")
    err = json.loads(tool_msg["content"])
    assert "Unknown Tool" in err["error"]