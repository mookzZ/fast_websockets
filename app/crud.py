from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from sqlalchemy.sql import func

from app import models, schemas
from app.auth.security import get_password_hash


def get_user(db: Session, user_id: int):
    """Получает пользователя по ID."""
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_username(db: Session, username: str):
    """Получает пользователя по имени пользователя."""
    return db.query(models.User).filter(models.User.username == username).first()


def create_user(db: Session, user: schemas.UserCreate):
    """Создает нового пользователя в базе данных."""
    hashed_password = get_password_hash(user.password)
    db_user = models.User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_chat(db: Session, chat_id: int):
    """Получает чат по ID."""
    return db.query(models.Chat).filter(models.Chat.id == chat_id).first()


def get_user_chats(db: Session, user_id: int):
    """Получает все чаты, в которых состоит пользователь."""
    return db.query(models.Chat).join(models.ChatMember).filter(models.ChatMember.user_id == user_id).all()


def create_chat(db: Session, chat: schemas.ChatCreate, creator_id: int):
    """Создает новый чат."""
    db_chat = models.Chat(
        name=chat.name,
        is_group_chat=chat.is_group_chat,
        creator_id=creator_id if chat.is_group_chat else None
    )
    db.add(db_chat)
    db.commit()
    db.refresh(db_chat)

    add_chat_member(db, chat_id=db_chat.id, user_id=creator_id)

    if chat.is_group_chat and chat.initial_members_ids:
        for member_id in chat.initial_members_ids:
            if member_id != creator_id:
                add_chat_member(db, chat_id=db_chat.id, user_id=member_id)

    return db_chat


def get_private_chat_between_users(db: Session, user1_id: int, user2_id: int):
    """Находит личный чат между двумя пользователями."""
    chat = db.query(models.Chat).filter(
        models.Chat.is_group_chat == False
    ).join(models.ChatMember).filter(
        or_(
            (models.ChatMember.user_id == user1_id),
            (models.ChatMember.user_id == user2_id)
        )
    ).group_by(models.Chat.id).having(
        func.count(models.ChatMember.user_id.distinct()) == 2
    ).first()
    return chat


def add_chat_member(db: Session, chat_id: int, user_id: int):
    """Добавляет пользователя в чат."""
    existing_member = db.query(models.ChatMember).filter(
        models.ChatMember.chat_id == chat_id,
        models.ChatMember.user_id == user_id
    ).first()
    if existing_member:
        return existing_member

    db_chat_member = models.ChatMember(chat_id=chat_id, user_id=user_id)
    db.add(db_chat_member)
    db.commit()
    db.refresh(db_chat_member)
    return db_chat_member


def remove_chat_member(db: Session, chat_id: int, user_id: int):
    """Удаляет пользователя из чата."""
    db_chat_member = db.query(models.ChatMember).filter(
        models.ChatMember.chat_id == chat_id,
        models.ChatMember.user_id == user_id
    ).first()
    if db_chat_member:
        db.delete(db_chat_member)
        db.commit()
        return True
    return False


def create_message(db: Session, message: schemas.MessageCreate, chat_id: int, sender_id: int):
    """Создает новое сообщение в чате."""
    db_message = models.Message(
        chat_id=chat_id,
        sender_id=sender_id,
        content=message.content
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message


def get_chat_messages(db: Session, chat_id: int, skip: int = 0, limit: int = 100):
    """Получает сообщения из конкретного чата."""
    messages = db.query(models.Message).options(joinedload(models.Message.sender)).filter(
        models.Message.chat_id == chat_id).order_by(models.Message.timestamp).all()
    return messages


def get_chat_members(db: Session, chat_id: int):
    """Получает всех участников чата."""
    return db.query(models.User).join(models.ChatMember).filter(models.ChatMember.chat_id == chat_id).all()