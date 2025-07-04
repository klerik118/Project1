from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from typing import Optional

from app.core.database import User


class UserRepository:

    @staticmethod
    async def checking_user_id(session: AsyncSession, id: int) -> Optional[int]:
        return await session.scalar(select(User.id).where(User.id == id))

    @staticmethod
    async def get_user_by_id(session: AsyncSession, id: int) -> Optional[User]:
        return await session.scalar(select(User).where(User.id == id))

    @staticmethod
    async def сhecking_user_existence_by_email(session: AsyncSession, email: str) -> Optional[str]:
        return await session.scalar(select(User.email).where(User.email == email))

    @staticmethod
    async def adding_user(session: AsyncSession, name: str, email: str, hashed_password):
        query = insert(User).values(name=name, email=email, hashed_password=hashed_password)
        await session.execute(query)
        await session.commit()

    @staticmethod
    async def get_user_by_email(session: AsyncSession, email: str) -> Optional[User]: 
        return await session.scalar(select(User).where(User.email == email))