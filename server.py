from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse

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

@app.websocket("/ws")
async def websocket_endpoint(socket: WebSocket):
    await socket.accept()
    while True:
        
        data = await socket.receive_text()
        response = await get_response(data)
        await socket.send_text(response)

# should be asyncronous as eventually reponse will be attained from llm call -- time intensive
async def get_response(message: str) -> str:
    print(message)
    split_message = message.strip().splitlines()
    print(split_message)

    # simple response from 'bot' for testing
    if("hi" in split_message or "hello" in split_message):
        return "Hey, What can I help you with today?"
    elif("bye" in split_message):
        return "Goodbye, hopefully I helped you today!"

