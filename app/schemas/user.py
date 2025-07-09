from enum import StrEnum
from decimal import Decimal
from typing import List

from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from redis.asyncio import Redis

from app.core.database import get_async_session, get_redis
from app.core.security import get_id_current_user


class UserLogin(BaseModel):
    email: EmailStr = 'email'
    password: str = Field('string', min_length=5, max_length=20, pattern=r'^[a-zA-Z0-9]+$')


class UserCreate(UserLogin):
    name: str = Field('', min_length=3, max_length=50)
    

class UserOutId(BaseModel):
    id: int


class UserOut(UserOutId):
    name: str
    email: str
    date_registration: str


class TypeCategory(StrEnum):
    INCOME = 'income'
    EXPENSES = 'expenses'
    

class CategoryCreate(BaseModel):
    name: str = Field('', min_length=1, max_length=50)
    type: TypeCategory = ''
    description: str


class CategoryOut(CategoryCreate):
    id: int
    id_user: int


class UpdateCategory(BaseModel):
    id: int
    new_name: str = Field('', min_length=1, max_length=50)
    new_type_category: TypeCategory = ''
    new_description: str


class TransacrionsOut(BaseModel):
    id: int
    name: str
    type: str
    amount: float
    date: str
    description: str


class TransactionCreate(BaseModel):
    category: str 
    amount: Decimal = Field(0, decimal_places=2, gt=Decimal('0.00'), le=Decimal('100000000.00'))
    description: str


class TransactionUpdate(TransactionCreate):
    id_transaction: int


class CategoryDepends:
    def __init__(
            self, 
            session: AsyncSession = Depends(get_async_session),
            user_id: UserOutId = Depends(get_id_current_user),
            redis_app: Redis = Depends(get_redis)  
            ):
        self.session = session
        self.user_id = user_id
        self.redis_app = redis_app


class TransactionDepends:
    def __init__(
            self, 
            session: AsyncSession = Depends(get_async_session), 
            user_id: UserOutId = Depends(get_id_current_user)
            ):
        self.session = session
        self.user_id = user_id


class WsChat(BaseModel):
    recipient: List[int] = []
    message: str = ''
    group: bool = False