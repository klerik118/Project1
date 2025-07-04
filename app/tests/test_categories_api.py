import pytest
from httpx import AsyncClient
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from passlib.hash import pbkdf2_sha256 

from app.core.database import User, Category
from app.tests.conftest import valid_token, invalid_token


@pytest.mark.asyncio
@pytest.mark.parametrize(
        "name, type, description, expected_status, expected_detail", [
    ("Зарплата", "income", "Описание", status.HTTP_200_OK, "Category Зарплата successfully added"),
    ("Продукты", "expenses", "Описание", status.HTTP_200_OK, "Category Продукты successfully added"),
    ("Зарплата", "income", "Описание", status.HTTP_403_FORBIDDEN, "This category already exists"),
    ("Зарплата", "invalid", "Описание", status.HTTP_422_UNPROCESSABLE_ENTITY, "Data entered incorrectly"),
    ("", "income", "Описание", status.HTTP_422_UNPROCESSABLE_ENTITY, "Data entered incorrectly"),
    ("Другое", "income", "Описание", status.HTTP_401_UNAUTHORIZED, "Token expired"),
    ]
)
async def test_add_category(
    name: str,
    type: str,
    description: str,
    expected_status: int, 
    expected_detail: str, 
    client: AsyncClient, 
    session_db: AsyncSession,
    ):
    id = await session_db.scalar(select(User.id).where(User.email == 'dol@email.ru'))
    if not id:
        hashed_password = pbkdf2_sha256.hash('password')
        query = insert(User).values(name="dolid", email='dol@email.ru', hashed_password=hashed_password)
        await session_db.execute(query)
        await session_db.commit()
        id = await session_db.scalar(select(User.id).where(User.email == 'dol@email.ru'))
    payload = {'name': name, 'type': type, 'description': description}
    token = await invalid_token(id) if expected_detail == "Token expired" else await valid_token(id)
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.post("/categories", json=payload, headers=headers)
    assert response.status_code == expected_status


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'expected_status, expected_detail', [
    (status.HTTP_200_OK, None),
    (status.HTTP_401_UNAUTHORIZED, "Token expired")
    ]
)
async def test_get_all_cagerories(
    expected_status: int,
    expected_detail: str,
    client: AsyncClient, 
    session_db: AsyncSession,
    ):
    id = await session_db.scalar(select(User.id).where(User.email == 'dol@email.ru'))
    if not id:
        hashed_password = pbkdf2_sha256.hash('password')
        query = insert(User).values(name="dolid", email='dol@email.ru', hashed_password=hashed_password)
        await session_db.execute(query)
        await session_db.commit()
        id = await session_db.scalar(select(User.id).where(User.email == 'dol@email.ru'))
        test_categories = [
            {'name': 'Зарплата', 'type': 'income', 'description': 'Описание'},
            {'name': 'Продукты', 'type': 'expenses', 'description': 'Описание'}
            ]
        for category in test_categories:
            query = insert(Category).values(
                name=category['name'], 
                type=category['type'], 
                description=category['description'], 
                user_id=id,
                )
            await session_db.execute(query)
            await session_db.commit()
    token = await invalid_token(id) if expected_detail == "Token expired" else await valid_token(id)
    response = await client.get("/categories", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == expected_status
 

@pytest.mark.asyncio
@pytest.mark.parametrize(
        "name, type, description, expected_status, expected_detail", [
    ("Зарплата", "income", "Заработная плата", status.HTTP_200_OK, 'Category changed'),
    ("Продукты", "income", "Описание", status.HTTP_404_NOT_FOUND, "such a category already exists"),
    ("Зарплата", "invalid", "Описание", status.HTTP_422_UNPROCESSABLE_ENTITY, None),
    ("", "income", "Описание", status.HTTP_422_UNPROCESSABLE_ENTITY, None),
    ("Другое", "income", "Описание", status.HTTP_401_UNAUTHORIZED, "Expired token"),
    ])
async def test_update_category(
    name: str,
    type: str,
    description: str,
    expected_status: int,
    expected_detail: str,
    client: AsyncClient, 
    session_db: AsyncSession,
    ):
    id = await session_db.scalar(select(User.id).where(User.email == 'dol@email.ru'))
    if not id:
        hashed_password = pbkdf2_sha256.hash('password')
        query = insert(User).values(name="dolid", email='dol@email.ru', hashed_password=hashed_password)
        await session_db.execute(query)
        await session_db.commit()
        id = await session_db.scalar(select(User.id).where(User.email == 'dol@email.ru'))
        test_categories = [
            {'name': 'Зарплата', 'type': 'income', 'description': 'Описание'},
            {'name': 'Продукты', 'type': 'expenses', 'description': 'Описание'}
            ]
        for category in test_categories:
            query = insert(Category).values(
                name=category['name'], 
                type=category['type'], 
                description=category['description'], 
                user_id=id,
                )
            await session_db.execute(query)
            await session_db.commit
    id_category = await session_db.scalar(select(Category.id).where(Category.name == 'Зарплата'))
    payload = {'id': id_category, 'new_name': name, 'new_type_category': type, 'new_description': description}
    token = await invalid_token(id) if expected_detail == "Expired token" else await valid_token(id)
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.put("/categories", json=payload, headers=headers)
    assert response.status_code == expected_status
    if expected_detail:
       assert expected_detail in response.text


@pytest.mark.asyncio 
@pytest.mark.parametrize(
    "id_category, expected_status, expected_detail", [
    (1, status.HTTP_200_OK, 'Category № 1 deleted'),
    (99, status.HTTP_404_NOT_FOUND, 'No such category'),
    ('invalid', status.HTTP_422_UNPROCESSABLE_ENTITY, 'Data entered incorrectly'),
    (-99, status.HTTP_404_NOT_FOUND, 'No such category'),
    (1, status.HTTP_401_UNAUTHORIZED, "Expired token")
    ])
async def test_delete_category(
    id_category: int,
    expected_status: int,
    expected_detail: str,
    client: AsyncClient, 
    session_db: AsyncSession,
    ):
    id_user = await session_db.scalar(select(User.id).where(User.email == 'dol@email.ru'))
    if not id_user:
        hashed_password = pbkdf2_sha256.hash('password')
        query = insert(User).values(name="dolid", email='dol@email.ru', hashed_password=hashed_password)
        await session_db.execute(query)
        await session_db.commit()
        id_user = await session_db.scalar(select(User.id).where(User.email == 'dol@email.ru'))
        test_categories = [
            {'name': 'Зарплата', 'type': 'income', 'description': 'Описание'},
            {'name': 'Продукты', 'type': 'expenses', 'description': 'Описание'}
            ]
        for category in test_categories:
            query = insert(Category).values(
                name=category['name'], 
                type=category['type'], 
                description=category['description'], 
                user_id=id_user,
                )
            await session_db.execute(query)
            await session_db.commit()
    token = await invalid_token(id_user) if expected_detail == "Expired token" else await valid_token(id_user)
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.request("DELETE", "/categories", json={'id': id_category}, headers=headers)
    assert response.status_code == expected_status  
    if expected_status != 422:
        assert expected_detail in response.text
