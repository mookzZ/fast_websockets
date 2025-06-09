from datetime import datetime

from pydantic import BaseModel, Field
from typing import Optional, List

class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=50)

class UserCreate(UserBase):
    password: str = Field(min_length=6)

class UserLogin(BaseModel):
    username: str
    password: str

class UserInDB(UserBase):
    id: int

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: Optional[str] = None

class UserInDB(UserBase):
    """Схема пользователя, как он хранится в БД (без пароля)."""
    id: int

    class Config:
        from_attributes = True

class ChatMemberUser(BaseModel):
    """Вложенная схема для пользователя в рамках ChatMember."""
    id: int
    username: str

    class Config:
        from_attributes = True

class ChatMember(BaseModel):
    """Схема для участника чата, включая информацию о пользователе."""
    id: int
    user_id: int
    chat_id: int
    joined_at: datetime
    user: ChatMemberUser

    class Config:
        from_attributes = True

class MessageBase(BaseModel):
    content: str = Field(..., min_length=1)

class MessageCreate(MessageBase):
    pass

class Message(MessageBase):
    id: int
    chat_id: int
    sender_id: int
    timestamp: datetime
    sender: UserInDB

    class Config:
        from_attributes = True

class MessageResponse(BaseModel):
    """Схема для сообщений, возвращаемых через API (включая имя отправителя)."""
    id: int
    chat_id: int
    sender_id: int
    content: str
    timestamp: datetime
    sender_username: Optional[str] = None # Это поле будет содержать имя отправителя

    class Config:
        from_attributes = True

class ChatBase(BaseModel):
    name: Optional[str] = None
    is_group_chat: bool = False

class ChatCreate(ChatBase):
    target_user_id: Optional[int] = None
    initial_members_ids: Optional[List[int]] = None

class Chat(ChatBase):
    id: int
    creator_id: Optional[int] = None
    created_at: datetime
    messages: List[Message] = []
    members: List[ChatMember] = []

    class Config:
        from_attributes = True