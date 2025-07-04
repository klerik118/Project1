import pytest
from httpx import AsyncClient
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from passlib.hash import pbkdf2_sha256 
import jwt

from app.core.database import User
from app.core.config import auth
from app.tests.conftest import valid_token, invalid_token


@pytest.mark.parametrize(
    "test_user, expected_status, expected_message",
    [
        (
            {
                "name": "TestUser1",
                "email": "test1@gmail.com",
                "password": "securepassword123"
            },
            status.HTTP_200_OK,
            'User with email test1@gmail.com successfully added'
        ),
        (
            {
                "name": "TestUser1",
                "email": "test1@gmail.com",
                "password": "securepassword123"
            },
            status.HTTP_401_UNAUTHORIZED,
            'A user with this email is already registered'
        ),
        (
            {
                "name": "TestUser2",
                "email": "not-an-email",
                "password": "securepassword123"
            },
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            'Data entered incorrectly'  
        ),
        (
            {
                "name": "TestUser3",
                "email": "test3@gmail.com",
                "password": "shor"
            },
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            'Data entered incorrectly'
        ),
        (
            {
                "name": "", 
                "email": "john.doe3@example.com",
                "password": "short_password",
            },
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            'Data entered incorrectly' 
        ),
    ],
)
@pytest.mark.asyncio
async def test_user_registration(
    client: AsyncClient, 
    session_db: AsyncSession, 
    test_user: dict, 
    expected_status: int, 
    expected_message: str,
    ):
    response = await client.post('/registration', json=test_user)
    assert response.status_code == expected_status
    if expected_status == status.HTTP_200_OK:
        user = await session_db.scalar(select(User).where(User.email == test_user["email"]))
        assert user is not None
        assert user.name == test_user["name"]
        assert pbkdf2_sha256.verify(test_user["password"], user.hashed_password)


@pytest.mark.parametrize(
        "email, password, expected_status", 
        [
            ("valid@example.com", "strongpassword", status.HTTP_200_OK),
            ("valid@example.com", "wrongpassword", status.HTTP_401_UNAUTHORIZED),
            ("nonexistent@example.com", "anypassword", status.HTTP_401_UNAUTHORIZED),
            ("not-an-email", "anypassword", status.HTTP_422_UNPROCESSABLE_ENTITY)
            ]
        )
@pytest.mark.asyncio
async def test_user_login(
    
    email: str, 
    password: str, 
    expected_status: int, 
    client: AsyncClient, 
    session_db: AsyncSession
    ):
    if email == "valid@example.com" and expected_status == status.HTTP_200_OK:
        test_user = User(
            name='john',
            email="valid@example.com",
            hashed_password=pbkdf2_sha256.hash("strongpassword"),   
        )
        query = insert(User).values(
            name=test_user.name, 
            email=test_user.email, 
            hashed_password=test_user.hashed_password
            )
        await session_db.execute(query)
        await session_db.commit()
    response = await client.post("/login", json={"email": email, "password": password})
    assert response.status_code == expected_status
    if expected_status == status.HTTP_200_OK:
        token = response.json()
        assert isinstance(token['eccess_token'], str)
        decoded = jwt.decode(token['eccess_token'], auth.public_key_path.read_text(), auth.algorithm) 
        assert "sub" in decoded
        assert "exp" in decoded


@pytest.mark.parametrize(
        "email, password, expected_status, expected_detail", [
    ("valid77@example.com", "strongpassword", status.HTTP_200_OK, None),
    ("valid77@example.com", "strongpassword", status.HTTP_401_UNAUTHORIZED, "Token expired")
    ]
)
@pytest.mark.asyncio
async def test_get_current_user(
    email: str, 
    password: str,
    expected_status: int, 
    expected_detail: str,  
    client: AsyncClient, 
    session_db: AsyncSession,
    ):
    test_user = User(
            name='jony77',
            email="valid77@example.com",
            hashed_password=pbkdf2_sha256.hash(password),   
        )
    if expected_status == status.HTTP_200_OK:
        query = insert(User).values(
            name=test_user.name, 
            email=test_user.email, 
            hashed_password=test_user.hashed_password
            )
        await session_db.execute(query)
        await session_db.commit()
    user_id = await session_db.scalar(select(User.id).where(User.email == email))
    token = await valid_token(user_id)
    if expected_detail == "Token expired":
        token = await invalid_token(user_id)
    response = await client.get("/user-info", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == expected_status
    if expected_status == status.HTTP_200_OK:
        assert response.json()['name'] == test_user.name
        assert response.json()['email'] == test_user.email
    


        





    



