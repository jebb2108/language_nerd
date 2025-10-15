from typing import Dict, List, Optional

from fastapi import WebSocket


# Менеджер соединений для комнат
class ConnectionService:
    def __init__(self):
        # room_id -> list of WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # WebSocket -> user session data
        self.sessions: Dict[WebSocket, dict] = {}

    async def connect(self, websocket: WebSocket, room_id: str, user_data: dict):
        # Принимаем соединение
        await websocket.accept()

        # Добавляем в комнату
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)

        # Сохраняем сессию
        self.sessions[websocket] = {
            "room_id": room_id,
            "username": user_data["nickname"],
            "token": user_data.get("token")
        }

        return True

    def disconnect(self, websocket: WebSocket):
        # Удаляем из комнаты
        session = self.sessions.get(websocket)
        if session:
            room_id = session["room_id"]
            if room_id in self.active_connections:
                if websocket in self.active_connections[room_id]:
                    self.active_connections[room_id].remove(websocket)
                # Удаляем пустую комнату
                if not self.active_connections[room_id]:
                    del self.active_connections[room_id]

            # Удаляем сессию
            del self.sessions[websocket]

    async def broadcast_to_room(self, message: dict, room_id: str):
        if room_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[room_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.append(connection)

            # Удаляем отключенные соединения
            for connection in disconnected:
                self.disconnect(connection)

    async def get_user_session(self, websocket: WebSocket) -> Optional[dict]:
        return self.sessions.get(websocket)

    @staticmethod
    async def send_personal_message(message: dict, websocket: WebSocket):
        await websocket.send_json(message)


# Глобальный экземпляр менеджера
connection_service = ConnectionService()