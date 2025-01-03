from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI()

# In-memory state to track the LED status
led_state = {"on": False}

# A simple HTML page to control LED via web page
html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>LED Control</title>
</head>
<body>
    <h1>LED Control</h1>
    <button onclick="toggleLED('on')">Turn ON</button>
    <button onclick="toggleLED('off')">Turn OFF</button>

    <script>
        async function toggleLED(state) {
            await fetch(`/led/${state}`, { method: "POST" });
        }

        // Establish WebSocket connection
        const socket = new WebSocket("ws://localhost:5000/ws");

        // Handle messages from the server (LED state updates)
        socket.onmessage = function(event) {
            console.log("Received message: ", event.data);
            // You can add logic here to update the UI based on LED state
        };
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def get_html():
    return html_content

# Endpoint to handle LED on/off requests
@app.post("/led/{state}")
async def switch_led(state: str):
    if state == "on":
        led_state["on"] = True
    elif state == "off":
        led_state["on"] = False
    else:
        return {"error": "Invalid state"}
    # Notify WebSocket clients
    await notify_clients()
    return {"status": f"LED turned {state}"}

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except WebSocketDisconnect:
                self.disconnect(connection)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    # Send current LED state to the new client
    current_state = "on" if led_state["on"] else "off"
    await websocket.send_text(f"LED is {current_state}")
    
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"Error: {e}")
        manager.disconnect(websocket)

# Notify WebSocket clients when LED state changes
async def notify_clients():
    state = "on" if led_state["on"] else "off"
    await manager.broadcast(f"LED is {state}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
