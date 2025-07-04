from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete

from app.core.database import Category


class CategoryRepository:
        

    @staticmethod
    async def get_name_category(session: AsyncSession, user_id: int, name_category: str) -> Optional[str]: 
        query = select(Category.name).where(Category.id_user == user_id, Category.name == name_category)
        return await session.scalar(query)
    

    @staticmethod               
    async def create_new_category(session: AsyncSession, name: str, type: str, description: str, user_id: int):
        query = insert(Category).values(
            name=name,
            type=type,
            description=description, 
            id_user=user_id,
            )
        await session.execute(query)
        await session.commit()   


    @staticmethod
    async def get_categories(session: AsyncSession, user_id: int) -> Optional[list]:
        query = select(Category).where(Category.id_user == user_id)
        categories = await session.execute(query)
        return categories.scalars().all()


    @staticmethod
    async def get_category(session: AsyncSession, category_id: int, user_id: int) -> Optional[int]:
        query = select(Category).where(Category.id == category_id, Category.id_user==user_id)
        return await session.scalar(query)
    

    @staticmethod
    async def list_name_existing_categories(session: AsyncSession, user_id: int):
        query = select(Category.name).where(Category.id_user == user_id)
        categories = await session.execute(query)
        return categories.scalars().all()


    @staticmethod
    async def update_category(session: AsyncSession, category_id: int, name: str, type: str, description: str):
        query = update(Category).where(Category.id == category_id).values(
            name=name,  
            type=type,  
            description=description,
            )
        await session.execute(query)
        await session.commit()


    @staticmethod
    async def delete_category(session: AsyncSession, id_category: int):
        await session.execute(delete(Category).where(Category.id == id_category))
        await session.commit()