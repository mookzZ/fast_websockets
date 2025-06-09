from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from sqlalchemy.orm import Session
import json

from app.database import get_db
from app import crud, models, schemas
from app.auth.router import get_current_user
from app.api.websockets.ws_manager import manager

router = APIRouter()


@router.websocket("/ws/{chat_id}")
async def websocket_chat_endpoint(
        websocket: WebSocket,
        chat_id: int,
        db: Session = Depends(get_db)
):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user: models.User = None
    try:
        from app.auth.security import decode_access_token
        payload = decode_access_token(token)
        if payload is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        user = crud.get_user_by_username(db, username=username)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    chat = crud.get_chat(db, chat_id)
    if not chat:
        await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)
        print(f"Chat {chat_id} not found.")
        return

    is_member = any(member.user_id == user.id for member in chat.members)
    if not is_member:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        print(f"User {user.username} (ID: {user.id}) is not a member of chat {chat_id}.")
        return

    await manager.connect(user.id, websocket)
    print(f"WebSocket connected for user {user.username} to chat {chat_id}")

    try:
        while True:
            data = await websocket.receive_text()
            print(f"Received message from user {user.username} in chat {chat_id}: {data}")

            try:
                message_data = json.loads(data)
                message_type = message_data.get("type", "message")  # Ожидаем тип, по умолчанию "message"
                message_content = message_data.get("content")

                if message_type != "message" or not message_content:
                    await websocket.send_text(
                        json.dumps({"error": "Invalid message format, expected type 'message' and 'content'"}))
                    continue

            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "Message must be valid JSON"}))
                continue

            # Сохраняем сообщение в БД
            new_message_schema = schemas.MessageCreate(content=message_content)
            db_message = crud.create_message(db, new_message_schema, chat_id, user.id)

            # Формируем сообщение для рассылки
            message_to_send = {
                "type": "message",  # Указываем тип
                "chat_id": db_message.chat_id,
                "sender_id": db_message.sender_id,
                "sender_username": user.username,
                "content": db_message.content,
                "timestamp": db_message.timestamp.isoformat()
            }

            chat_members = crud.get_chat_members(db, chat_id)
            member_ids = [member.id for member in chat_members]

            await manager.broadcast_message_to_chat(json.dumps(message_to_send), member_ids)

    except WebSocketDisconnect:
        manager.disconnect(user.id, websocket)
        print(f"WebSocket disconnected for user {user.username} from chat {chat_id}")
    except Exception as e:
        print(f"WebSocket error for user {user.username} in chat {chat_id}: {e}")
        manager.disconnect(user.id, websocket)
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)