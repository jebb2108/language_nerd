from datetime import datetime
from typing import Dict, Optional

from fastapi import WebSocket
from config import config

from logging_config import opt_logger as log

logger = log.setup_logger('connection')


# Менеджер соединений для комнат с онлайн статусами
class ConnectionService:
    def __init__(self):
        # room_id -> dict of {username: WebSocket}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        # WebSocket -> user session data
        self.sessions: Dict[WebSocket, dict] = {}

    async def connect(self, websocket: WebSocket, room_id: str, user_data: dict):
        await websocket.accept()
        username = user_data["nickname"]

        # Добавляем в комнату
        if room_id not in self.active_connections:
            self.active_connections[room_id] = {}

        # Уведомляем партнера о подключении
        partner_ws = await self._get_partner_websocket(room_id, username)
        if partner_ws:
            try:
                await partner_ws.send_json({
                    "type": "partner_status",
                    "is_online": True
                })
            except Exception as e:
                logger.error(f"Error sending partner status: {e}")

        self.active_connections[room_id][username] = websocket

        # Сохраняем сессию
        self.sessions[websocket] = {
            "room_id": room_id,
            "username": username,
            "token": user_data.get("token")
        }

        # Отправляем текущий статус партнера новому пользователю
        partner_status = partner_ws is not None
        await self.send_personal_message({
            "type": "partner_status",
            "is_online": partner_status
        }, websocket)

        return True

    async def disconnect(self, websocket: WebSocket):
        session = self.sessions.get(websocket)
        if not session:
            return

        room_id = session["room_id"]
        username = session["username"]

        # Удаляем из комнаты
        if room_id in self.active_connections:
            if username in self.active_connections[room_id]:
                del self.active_connections[room_id][username]

            # Уведомляем партнера об отключении
            partner_ws = await self._get_partner_websocket(room_id, username)
            if partner_ws:
                try:
                    await partner_ws.send_json({
                        "type": "partner_status",
                        "is_online": False
                    })
                except Exception as e:
                    logger.error(f"Error sending partner offline status: {e}")

            # Удаляем пустую комнату
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]

        # Удаляем сессию
        if websocket in self.sessions:
            del self.sessions[websocket]

    async def _get_partner_websocket(self, room_id: str, current_username: str) -> Optional[WebSocket]:
        """Получает websocket партнера в чате (второго пользователя)"""
        if room_id not in self.active_connections:
            return None

        users_in_room = list(self.active_connections[room_id].keys())
        if len(users_in_room) == 0:
            return None

        # Находим партнера (другого пользователя в комнате)
        for username, ws in self.active_connections[room_id].items():
            if username != current_username:
                return ws

        return None

    async def broadcast_to_room(self, message: dict, room_id: str):
        """Рассылает сообщение всем участникам комнаты"""
        if room_id in self.active_connections:
            disconnected_users = []
            for username, connection in self.active_connections[room_id].items():
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected_users.append(username)

            # Удаляем отключенные соединения
            for username in disconnected_users:
                if username in self.active_connections[room_id]:
                    del self.active_connections[room_id][username]

    async def get_user_session(self, websocket: WebSocket) -> Optional[dict]:
        return self.sessions.get(websocket)

    @staticmethod
    async def send_personal_message(message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    def get_online_users(self, room_id: str) -> list:
        """Получает список онлайн пользователей в комнате"""
        if room_id in self.active_connections:
            return list(self.active_connections[room_id].keys())
        return []


# Глобальный экземпляр менеджера
connection_service = ConnectionService()