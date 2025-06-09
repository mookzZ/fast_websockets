import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app import crud, schemas, models
from app.database import get_db
from app.auth.router import get_current_user
from app.api.websockets.ws_manager import manager

router = APIRouter()


@router.post("/chats/", response_model=schemas.Chat, status_code=status.HTTP_201_CREATED)
def create_new_chat(
        chat_create: schemas.ChatCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    """
    Создает новый чат.
    - Если `is_group_chat` равно `False` (личный чат), `target_user_id` обязателен.
      Проверяет, существует ли уже чат между этими двумя пользователями.
    - Если `is_group_chat` равно `True` (групповой чат), `name` и `initial_members_ids` обязательны.
      Создатель чата автоматически добавляется как участник.
    """
    if chat_create.is_group_chat:
        if not chat_create.name:
            raise HTTPException(status_code=400, detail="Название группы обязательно для группового чата.")
        # Создаем групповой чат
        db_chat = crud.create_chat(db=db, chat=chat_create, creator_id=current_user.id)
    else:
        # Создаем личный чат
        if not chat_create.target_user_id:
            raise HTTPException(status_code=400, detail="Для личного чата требуется `target_user_id`.")

        if chat_create.target_user_id == current_user.id:
            raise HTTPException(status_code=400, detail="Нельзя создать личный чат с самим собой.")

        target_user = crud.get_user(db, chat_create.target_user_id)
        if not target_user:
            raise HTTPException(status_code=404, detail="Целевой пользователь не найден.")

        # Проверяем, существует ли уже личный чат между этими двумя пользователями
        existing_chat = crud.get_private_chat_between_users(db, current_user.id, chat_create.target_user_id)
        if existing_chat:
            return existing_chat  # Возвращаем существующий чат

        # Создаем новый личный чат
        chat_create.name = None  # Личные чаты обычно не имеют названия
        db_chat = crud.create_chat(db=db, chat=chat_create, creator_id=current_user.id)
        # Добавляем второго участника
        crud.add_chat_member(db, chat_id=db_chat.id, user_id=chat_create.target_user_id)

    return db_chat


@router.get("/chats/", response_model=List[schemas.Chat])
def get_user_chats(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    """Получает все чаты, в которых состоит текущий аутентифицированный пользователь."""
    chats = crud.get_user_chats(db, user_id=current_user.id)
    return chats


@router.get("/chats/{chat_id}", response_model=schemas.Chat)
def get_chat_by_id(
        chat_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    """Получает информацию о конкретном чате по ID."""
    db_chat = crud.get_chat(db, chat_id=chat_id)
    if not db_chat:
        raise HTTPException(status_code=404, detail="Чат не найден.")

    # Проверяем, является ли текущий пользователь участником этого чата
    is_member = any(member.user_id == current_user.id for member in db_chat.members)
    if not is_member:
        raise HTTPException(status_code=403, detail="У вас нет доступа к этому чату.")

    return db_chat


@router.post("/chats/{chat_id}/members", response_model=schemas.ChatMember, status_code=status.HTTP_201_CREATED)
async def add_member_to_chat(  # Добавляем async, так как будем использовать await
        chat_id: int,
        user_id_to_add: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    """
    Добавляет пользователя в групповой чат.
    Только создатель группы может приглашать других пользователей.
    """
    db_chat = crud.get_chat(db, chat_id=chat_id)
    if not db_chat:
        raise HTTPException(status_code=404, detail="Чат не найден.")

    if not db_chat.is_group_chat:
        raise HTTPException(status_code=400, detail="Нельзя добавлять участников в личный чат.")

    if db_chat.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Только создатель чата может добавлять участников.")

    user_to_add = crud.get_user(db, user_id_to_add)
    if not user_to_add:
        raise HTTPException(status_code=404, detail="Добавляемый пользователь не найден.")

    is_already_member = any(member.user_id == user_id_to_add for member in db_chat.members)
    if is_already_member:
        raise HTTPException(status_code=400, detail="Пользователь уже является участником этого чата.")

    db_chat_member = crud.add_chat_member(db, chat_id=chat_id, user_id=user_id_to_add)

    # --- НОВОЕ: Отправляем уведомление новому участнику через WebSocket ---
    notification_message = {
        "type": "chat_invite_notification",
        "chat_id": db_chat.id,
        "chat_name": db_chat.name or "Unnamed Group",
        "inviter_username": current_user.username
    }
    await manager.send_personal_message(json.dumps(notification_message), user_id_to_add)
    # ---------------------------------------------------------------------

    return db_chat_member


@router.delete("/chats/{chat_id}/members/{user_id_to_remove}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member_from_chat(
        chat_id: int,
        user_id_to_remove: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    """
    Удаляет пользователя из группового чата.
    Только создатель группы может удалить других пользователей.
    """
    db_chat = crud.get_chat(db, chat_id=chat_id)
    if not db_chat:
        raise HTTPException(status_code=404, detail="Чат не найден.")

    if not db_chat.is_group_chat:
        raise HTTPException(status_code=400, detail="Нельзя удалять участников из личного чата.")

    # Проверяем, является ли текущий пользователь создателем чата
    if db_chat.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Только создатель чата может удалять участников.")

    # Нельзя удалить самого себя из группы через этот эндпоинт, если ты создатель
    if db_chat.creator_id == user_id_to_remove:
        raise HTTPException(status_code=400, detail="Создатель не может быть удален из группы таким образом.")

    # Проверяем, является ли удаляемый пользователь членом чата
    is_member = any(member.user_id == user_id_to_remove for member in db_chat.members)
    if not is_member:
        raise HTTPException(status_code=404, detail="Пользователь не является участником этого чата.")

    # Удаляем участника
    success = crud.remove_chat_member(db, chat_id=chat_id, user_id=user_id_to_remove)
    if not success:
        raise HTTPException(status_code=500, detail="Не удалось удалить пользователя.")
    return


@router.get("/chats/{chat_id}/messages", response_model=List[schemas.MessageResponse])  # <-- ИЗМЕНИ ЭТО!
def get_chat_messages(
        chat_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    chat = crud.get_chat(db, chat_id=chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден.")

    # Проверяем, является ли текущий пользователь членом чата
    is_member = any(member.user_id == current_user.id for member in chat.members)
    if not is_member:
        raise HTTPException(status_code=403, detail="Вы не являетесь участником этого чата.")

    messages = crud.get_chat_messages(db, chat_id=chat_id)

    response_messages = []
    for msg in messages:
        sender_username = msg.sender.username if msg.sender else f"User {msg.sender_id}"
        response_messages.append(schemas.MessageResponse(  # <-- И ЗДЕСЬ ИСПОЛЬЗУЙ НОВУЮ СХЕМУ
            id=msg.id,
            chat_id=msg.chat_id,
            sender_id=msg.sender_id,
            content=msg.content,
            timestamp=msg.timestamp,
            sender_username=sender_username  # Вот это поле мы заполняем
        ))
    return response_messages