import json
from loguru import logger
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(
    prefix="/ws",
    tags=["websocket"],
    responses={404: {"description": "Not found"}})

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        logger.debug("Frontend connected!")
        self.active_connections.append(websocket)
        await websocket.send_json({"type": "health", "status": "running"})

    def disconnect(self, websocket: WebSocket):
        logger.debug("Frontend disconnected!")
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def send_log_message(self, message: str):
        await self.broadcast({"type": "log", "message": message})

    async def send_item_update(self, item: json):
        await self.broadcast({"type": "item_update", "item": item})

    async def broadcast(self, message: json):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except RuntimeError:
                self.active_connections.remove(connection)


manager = ConnectionManager()


@router.websocket("")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except RuntimeError:
        manager.disconnect(websocket)