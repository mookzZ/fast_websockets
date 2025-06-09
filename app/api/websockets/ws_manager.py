from typing import List, Dict
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import json

class WebSocketConnectionManager:
    """
    Менеджер для управления активными WebSocket-соединениями.
    Позволяет добавлять, удалять соединения и рассылать сообщения.
    """
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        """Устанавливает соединение для пользователя."""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        print(f"User {user_id} connected. Total connections for user: {len(self.active_connections[user_id])}")

    def disconnect(self, user_id: int, websocket: WebSocket):
        """Разрывает соединение для пользователя."""
        if user_id in self.active_connections and websocket in self.active_connections[user_id]:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
            print(f"User {user_id} disconnected. Remaining connections for user: {self.active_connections.get(user_id, [])}")


    async def send_personal_message(self, message: str, user_id: int):
        """Отправляет персональное сообщение всем активным соединениям пользователя."""
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(message)
                except RuntimeError as e:
                    print(f"Failed to send message to user {user_id}: {e}")

    async def broadcast_message_to_chat(self, message: str, chat_members_ids: List[int]):
        """Рассылает сообщение всем участникам чата, у которых есть активные соединения."""
        for user_id in chat_members_ids:
            if user_id in self.active_connections:
                for connection in self.active_connections[user_id]:
                    try:
                        await connection.send_text(message)
                    except RuntimeError as e:
                        print(f"Failed to send message to user {user_id} in broadcast: {e}")

manager = WebSocketConnectionManager()