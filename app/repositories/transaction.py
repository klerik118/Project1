from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete, join
from fastapi import HTTPException

from app.core.database import Category, Transaction
  

class TransactionRepository:


    @staticmethod
    async def check_category_existence(
        session: AsyncSession, 
        user_id: int, 
        category_name: str
        ) -> Optional[Category]:
        query = select(Category).where(Category.id_user == user_id, Category.name == category_name)
        return await session.scalar(query)
    

    @staticmethod
    async def add_transaction(
        session: AsyncSession, 
        id_user: int, 
        amount: int, 
        type: str, 
        description: str, 
        category_id: str
        ):
        query = (insert(Transaction).values(
            id_user=id_user, 
            amount=amount,
            type=type,
            description=description,
            id_category=category_id,
            ))
        await session.execute(query)
        await session.commit()


    @staticmethod
    async def all_incom_expenses_one(session: AsyncSession, user_id: int, data: str) -> Optional[list]:
        j = join(Transaction, Category, Transaction.id_category == Category.id)
        query = select(
            Transaction.id, 
            Category.name, 
            Transaction.type, 
            Transaction.amount, 
            Transaction.date,
            Transaction.description,
            ).select_from(j).where(Transaction.id_user == user_id)
        if data.isdigit():
            query = query.where(Transaction.id == int(data))
        elif data == 'income' or data == 'expenses':
            query = query.where(Transaction.type == data)
        result = await session.execute(query)
        return result.mappings().all()


    @staticmethod
    async def check_transaction_existence(session: AsyncSession, user_id: int, transaction_id: int) -> Optional[int]:
        qwery = select(Transaction.id).where(Transaction.id_user == user_id, Transaction.id == transaction_id)
        return await session.scalar(qwery)
    

    @staticmethod
    async def update_transaction(
        session: AsyncSession, 
        id_transaction: int, 
        category_id: int, 
        new_amount: int, 
        new_description: str, 
        category_type: str
        ):
        query = update(Transaction).where(Transaction.id == id_transaction).values(
            id_category=category_id, 
            amount=new_amount,
            description=new_description,
            type=category_type,
            )
        await session.execute(query)
        await session.commit()


    @staticmethod
    async def delete_transaction(session: AsyncSession, transaction_id: int):
        await session.execute(delete(Transaction).where(Transaction.id == transaction_id))
        await session.commit()


