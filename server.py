from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse

from models.chat_manager import ChatManager
from models.chat_state import ChatState


from starlette.websockets import WebSocketDisconnect

# for database persistence
import uuid
from db.chat_db import SqliteChatRepo

app = FastAPI()


html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var ws = new WebSocket("ws://localhost:8000/ws");
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""

@app.get("/")
async def get():
    return HTMLResponse(html)

# set up storage once
db = SqliteChatRepo()

@app.websocket("/ws")
async def websocket_endpoint(socket: WebSocket):
    await socket.accept()

    session_id = str(uuid.uuid4())
    db.create_session(session_id)
    db.add_event(session_id, "session_started", {"source": "websocket"})

    # first create a chat state on per connection basis
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
        pass

# should be asyncronous as eventually reponse will be attained from llm call -- time intensive
async def get_response(message: str, state: ChatState) -> str:
    stripped_message = message.strip()
    return await ChatManager.handle_client_input(stripped_message, state)

