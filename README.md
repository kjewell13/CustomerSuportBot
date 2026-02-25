```txt
# AI Customer Support Bot — Full-Stack Template

A local, full-stack **AI customer support agent template** designed for learning, demos, and extension into real systems.

This project demonstrates how to:
- Build an **LLM-driven intent router**
- Handle **tool calling** (order lookup, knowledge base search)
- Maintain **conversation state**
- Persist chats with **SQLite**
- Connect a **React frontend to a FastAPI backend via WebSockets**
- Write **robust pytest coverage** for async + LLM-style code

The repository is intentionally structured to be **readable, testable, and reusable** as a starting point for real support agents.

---

## Demo Overview

### High-level flow

1. User opens the React web UI
2. UI opens a **WebSocket** connection to the backend
3. User sends a message
4. Backend:
   - Stores the message
   - Routes intent using an LLM
   - Requests missing slots (e.g. `order_id`) if needed
   - Calls tools (`get_order`, `knowledge_search`) when appropriate
   - Generates a final response
5. Response is sent back to the browser over WebSocket
6. Chat history is stored in SQLite

---

## Tech Stack

### Backend
- Python **3.14.2**
- FastAPI
- Uvicorn
- OpenAI (async client)
- SQLite
- python-dotenv

### Frontend
- React
- Vite
- WebSocket API

### Testing
- pytest
- pytest-asyncio
- pytest-cov

---

## Project Structure

```txt
server.py                # FastAPI app + WebSocket endpoint
llm_router.py            # Intent routing + response generation + tool calls

db/
  __init__.py
  init_db.py             # SQLite schema creation
  chat_db.py             # SQLite repository layer

models/
  intent.py
  chat_state.py
  knowledge_search.py    # Markdown-based knowledge search

demo-frontend/           # React/Vite demo UI
tests/                   # Pytest unit tests
````

---

## How the WebSocket Works

### Frontend (React)

The frontend opens a WebSocket connection when the chat component mounts:

```ts
const ws = new WebSocket("/ws"); // proxied by Vite
```

**What this does:**

* `/ws` is proxied by Vite to the FastAPI backend during development
* The browser performs a WebSocket handshake with the server
* The connection stays open for real-time, bidirectional messaging

**Frontend behavior:**

* User messages are sent via `ws.send(text)`
* Server messages are received via `ws.onmessage`
* Connection state is tracked as:

  * `connecting`
  * `connected`
  * `disconnected`

Incoming messages from the backend are appended to the chat UI as assistant responses.

---

### Backend (FastAPI)

The backend defines a WebSocket endpoint:

```py
@app.websocket("/ws")
async def websocket_endpoint(socket: WebSocket):
    await socket.accept()

    session_id = str(uuid.uuid4())
    db.create_session(session_id)
    db.add_event(session_id, "session_started", {"source": "websocket"})

    state = ChatState()
    state.user_data["session_id"] = session_id

    try:
        while True:
            data = await socket.receive_text()
            db.add_message(session_id, "user", data)

            response = await get_response(data, state)
            db.add_message(session_id, "assistant", response)

            await socket.send_text(response)
    except WebSocketDisconnect:
        db.add_event(session_id, "session_closed", {})
```

**Key design points:**

* One **WebSocket connection = one conversation**
* Each connection gets a unique `session_id`
* `ChatState` is kept in memory per connection
* All messages and lifecycle events are persisted to SQLite
* The connection is gracefully cleaned up on disconnect

---

## Intent Routing & Tool Calls

### Intent routing (`get_intent`)

The LLM is prompted to:

* Classify user intent (greeting, order lookup, refund, knowledge question, etc.)
* Decide the next action:

  * Respond directly
  * Ask for a missing slot (e.g. `order_id`)
  * Call a tool

This keeps decision logic centralized and easy to extend.

---

### Tools Available

* `get_order(order_id)`

  * Mock order lookup
  * Designed to be replaced with a real DB or API call

* `knowledge_search(query, top_k)`

  * Searches a Markdown-based knowledge base
  * Returns relevant policy or FAQ content

---

### Response Generation (`generate_result`)

1. If no tool is required → respond immediately
2. If a tool is required:

   * LLM requests a tool call
   * Backend executes the tool
   * Tool output is sent back to the LLM
   * LLM generates the final user-facing response

This mirrors real-world LLM tool-calling workflows.

---

## Knowledge Base Search

Knowledge search is **file-based, deterministic, and transparent**.

### Expected Markdown Format

```md
# Document Title

## Section Title
Content here...
```

### How It Works

* Reads `.md` files from a folder (default: `knowledge/`)
* Splits documents into chunks by `##` headings
* Tokenizes the user query
* Scores chunks using keyword frequency
* Returns top-matching sections (with truncation for long content)

This approach is simple, inspectable, and easy to replace later with embeddings or vector search.

---

## Database & Persistence

SQLite is used for simplicity and local demos.

### Stored Data

* Chat sessions
* Messages (user and assistant)
* Session lifecycle events

### Files

* `db/init_db.py` — schema creation
* `db/chat_db.py` — repository layer

Database access is handled through explicit context managers to avoid connection leaks and improve testability.

---

## Setup Instructions

### 1) Python Environment

Verify Python version:

```bash
python --version
# 3.14.2
```

Create and activate a virtual environment:

```bash
python3.14 -m venv .venv
source .venv/bin/activate
```

---

### 2) Install Dependencies

Runtime dependencies (`requirements.txt`):

```txt
fastapi
uvicorn[standard]
openai
python-dotenv
```

Install:

```bash
pip install -r requirements.txt
```

Development/testing dependencies (`requirements-dev.txt`):

```txt
pytest
pytest-asyncio
pytest-cov
```

Install:

```bash
pip install -r requirements-dev.txt
```

---

### 3) Environment Variables

Create a `.env` file in the project root:

```bash
OPENAI_API_KEY=your_openai_key_here
```

---

## Running the Demo Locally

### Terminal 1 — Backend (virtual environment)

Development mode (auto-reload):

```bash
uvicorn server:app --reload
```

Standard run:

```bash
uvicorn server:app
```

---

### Terminal 2 — Frontend

```bash
cd demo-frontend
npm install
npm run dev
```

Open the URL shown by Vite (usually `http://localhost:5173`).

---

## Running Tests

Run all tests:

```bash
pytest
```

Run with coverage:

```bash
pytest --cov=. --cov-report=term-missing
```

Tests cover:

* SQLite repository logic
* Knowledge search behavior
* LLM routing and response generation (with mocked OpenAI client)

---

## Using This Repo as a Template

### Replace the Knowledge Base

* Add your own Markdown files
* Keep the `#` / `##` heading structure
* Point `knowledge_search` to a different folder if needed

### Replace Order Lookup

* Swap `get_order(order_id)` with:

  * A database query
  * An API call
  * A service client

### Extend Intents

* Add new intents in `models/intent.py`
* Update router prompts and tool schema
* Add tests for new logic branches

### Swap Database

* SQLite is used for simplicity
* Repository pattern makes migration to Postgres straightforward

### Swap LLM Provider

* OpenAI is used by default
* LLM routing and generation are isolated for easy replacement

---

## Testing Philosophy

* Deterministic unit tests
* External systems (LLMs, filesystem, APIs) are mocked
* Async paths are explicitly tested
* Coverage emphasizes **logic and branching**, not prompt text

---

## Audience & Purpose

This project is intended for:

* **Recruiters / interviewers** evaluating backend & system design skills
* **Engineers** seeking a clean support-agent template
* **Students** learning async Python, WebSockets, and LLM tool routing

It is deliberately:

* Readable over clever
* Explicit over magical
* Testable over opaque

---

## Optional: Makefile

```makefile
.PHONY: backend frontend test coverage

backend:
	uvicorn server:app --reload

frontend:
	cd demo-frontend && npm run dev

test:
	pytest

coverage:
	pytest --cov=. --cov-report=term-missing
```

Usage:

* `make backend`
* `make frontend`
* `make test`
* `make coverage`

---

## License

Add a license (MIT is recommended) if you plan to open-source this template.

```
```
