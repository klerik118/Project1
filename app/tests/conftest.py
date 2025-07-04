from unittest.mock import AsyncMock
from datetime import datetime, timezone, timedelta
import sys
from pathlib import Path

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
import pytest_asyncio
from sqlalchemy.pool import NullPool
import jwt

sys.path.append(str(Path(__file__).parent.parent.parent))

from app.core.database import User, Category, Base, get_async_session, get_redis
from main import app
from app.core.config import auth
#from app.routes.categories import category_router


@pytest.fixture(scope='function')
def mock_async_session():
    return AsyncMock()


@pytest.fixture
def sample_user():
    return User(
        id=1,
        name="Test User",
        email="test@example.com",
        hashed_password="hashed123",
        date_registration=datetime.now()
    )


@pytest.fixture
def sample_category():
    return {
        "name": "Food",
        "type": "income",
        "description": "Test description",
        "id_user": 1
    }


@pytest.fixture
def sample_categories():
    return [
        Category(id=1, name="Food", type="expense", description="Groceries", id_user=1),
        Category(id=2, name="Transport", type="expense", description="Public transport", id_user=1),
    ]


@pytest_asyncio.fixture(scope="session")
async def engine():
    db_url = "postgresql+asyncpg://postgres:654321@localhost:5432/test"
    engine = create_async_engine(db_url, poolclass=NullPool)   
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine 
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def session_db(engine):
    async_session = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        yield session
    

@pytest_asyncio.fixture
async def mock_redis():
    redis = AsyncMock()
    redis.hgetall.return_value = {}
    redis.get.return_value = ''
    redis.hset.return_value = True
    redis.expire.return_value = True
    yield redis


@pytest_asyncio.fixture
async def client(session_db, mock_redis):
    app.dependency_overrides[get_async_session] = lambda: session_db
    app.dependency_overrides[get_redis] = lambda: mock_redis
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        yield client


async def valid_token(id):
    if id:
        private_key = auth.private_key_path.read_text()  
        algorithm = auth.algorithm    
        expire = datetime.now(timezone.utc) + timedelta(minutes=150)
        payload = {"sub": str(id), "exp": expire, 'type': 'access'}
        encode_jwt = jwt.encode(payload, private_key, algorithm=algorithm)
        return encode_jwt  
    else:
        return None


async def invalid_token(id):
    private_key = auth.private_key_path.read_text()  
    algorithm = auth.algorithm    
    expire = datetime.now(timezone.utc) - timedelta(minutes=1000)
    payload = {"sub": str(id), "exp": expire, 'type': 'access'}
    encode_jwt = jwt.encode(payload, private_key, algorithm=algorithm)
    return encode_jwt