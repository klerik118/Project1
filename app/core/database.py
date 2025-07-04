from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Enum, Integer, String, ForeignKey, DateTime, Numeric, func
from sqlalchemy_utils import EmailType
from redis.asyncio import Redis

from app.core.config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD


DB_URL = f'postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'


engine = create_async_engine(DB_URL)


SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)


type_category = Enum('income', 'expenses', name='categorytype')


class Base(DeclarativeBase):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, unique=True, autoincrement=True)


class User(Base):
    __tablename__ = 'users'
    name: Mapped[str] = mapped_column(String(20))
    email: Mapped[str] = mapped_column(EmailType, unique=True)
    hashed_password: Mapped[str] = mapped_column(String)
    date_registration: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=func.timezone('UTC', func.now()),
        )
    

class Category(Base):   
    __tablename__ = 'categories'
    name: Mapped[str] = mapped_column(String(30))
    type: Mapped[str] = mapped_column(type_category, nullable=False)
    description: Mapped[str] = mapped_column(String(50))
    id_user: Mapped[int] = mapped_column(ForeignKey('users.id'))


class Transaction(Base):  
    __tablename__ = 'transactions'
    id_user: Mapped[int] = mapped_column(ForeignKey('users.id'))
    amount: Mapped[Decimal] = mapped_column(Numeric(11, 2))
    type: Mapped[str] = mapped_column(type_category, nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.timezone('UTC', func.now()))
    description: Mapped[str] = mapped_column(String(50))
    id_category: Mapped[int] = mapped_column(ForeignKey('categories.id', ondelete='SET NULL'), nullable=True)


async def get_async_session():
    async with SessionLocal() as session:
        yield session


async def get_redis():
    redis_app = await Redis.from_url('redis://redis:6379', decode_responses=True)
    try:
        yield redis_app
    finally:
        await redis_app.close()
