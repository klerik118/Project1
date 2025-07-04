import pytest
from httpx import AsyncClient
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from passlib.hash import pbkdf2_sha256 
#from unittest.mock import AsyncMock, patch

from app.core.database import User, Category, Transaction
from app.tests.conftest import valid_token, invalid_token


async def filling_out_test_willow(session_db: AsyncSession):
    user_test = [
        {"name": "TestUser11", "email": "test11@gmail.com", "password": "password123"},
        {"name": "TestUser21", "email": "test21@gmail.com", "password": "password456"}
        ]
    for test in user_test:
        hashed_password=pbkdf2_sha256.hash(test['password'])
        query = insert(User).values(name=test['name'], email=test['email'], hashed_password=hashed_password)
        await session_db.execute(query)
        await session_db.commit()
    user_1 = await session_db.scalar(select(User.id).where(User.email == 'test11@gmail.com'))
    user_2 = await session_db.scalar(select(User.id).where(User.email == 'test21@gmail.com'))
    category_users = [
        {'name':'Зарплата', 'type':'income', 'description':'Описание', 'id_user': user_1},
        {'name':'Продукты', 'type':'expenses', 'description':'Описание', 'id_user': user_1},
        {'name':'Проценты', 'type':'income', 'description':'Описание', 'id_user': user_2},
        {'name':'Автомобиль', 'type':'expenses', 'description':'Описание', 'id_user': user_2}
        ]
    for category in category_users:
        query = insert(Category).values(
            name=category['name'],
            type=category['type'],
            description=category['description'], 
            id_user=category['id_user'],
            )
        await session_db.execute(query)
        await session_db.commit()
    id_cat = []
    for name in category_users:
        id_category = await session_db.scalar(select(Category.id).where(Category.name == name['name']))
        id_cat.append(id_category)
    transaction_user = [
        {'id_user': user_1, 'amount': 9000, 'type': 'income', 'description': 'Описание', 'id_category': id_cat[0]},
        {'id_user': user_1, 'amount': 3000, 'type': 'expenses', 'description': 'Описание', 'id_category': id_cat[1]},
        {'id_user': user_2, 'amount': 5000, 'type': 'income', 'description': 'Описание', 'id_category': id_cat[2]},
        {'id_user': user_2, 'amount': 4500, 'type': 'expenses', 'description': 'Описание', 'id_category': id_cat[3]},
        ]
    for tran in transaction_user:
        query = (insert(Transaction).values(
            id_user=tran['id_user'], 
            amount=tran['amount'],
            type=tran['type'],
            description=tran['description'],
            id_category=tran['id_category'],
            ))
        await session_db.execute(query)
        await session_db.commit()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "name_category, amount, description, expected_status, expected_detail", [
        ('Зарплата', 5555, 'Описание', status.HTTP_200_OK, None),
        ('Отпуск', 2000, 'Описание', status.HTTP_404_NOT_FOUND, 'No such category'),
        ('Зарплата', -5000, 'Описание', status.HTTP_422_UNPROCESSABLE_ENTITY, "Data entered incorrectly"),
        ('Зарплата', 0, 'Описание', status.HTTP_422_UNPROCESSABLE_ENTITY, "Data entered incorrectly")
        ]
    )
async def test_add_new_transaction(
    name_category: str,
    amount: int,
    description: str,
    expected_status: str,
    expected_detail: str,
    client: AsyncClient, 
    session_db: AsyncSession,
    mocker
    ):
    mocker.patch('app.core.tasks.process_task_celery.delay', return_value=True)
    id = await session_db.scalar(select(User.id).where(User.email == 'test11@gmail.com'))
    if not id:
        await filling_out_test_willow(session_db)
    id = await session_db.scalar(select(User.id).where(User.email == 'test11@gmail.com'))
    token = await invalid_token(id) if expected_detail == "Token expired" else await valid_token(id)
    headers = {"Authorization": f"Bearer {token}"}
    payload = {'category': name_category, 'amount': amount, 'description': description}
    response = await client.post("/transactions", json=payload, headers=headers)
    assert response.status_code == expected_status
    if expected_status == 200:
        transaction = await session_db.scalar(select(Transaction).where(Transaction.amount == 5555))
        assert transaction.id_user == id


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data, expected_status, expected_detail", [
        ('all', status.HTTP_200_OK, None),
        ('income', status.HTTP_200_OK, None),
        ('expenses', status.HTTP_200_OK, None),
        ('invalid', status.HTTP_422_UNPROCESSABLE_ENTITY, "Data entered incorrectly"),
        (1, status.HTTP_200_OK, None),
        (88, status.HTTP_404_NOT_FOUND, 'No such transactions'),
        (-88, status.HTTP_422_UNPROCESSABLE_ENTITY, "Data entered incorrectly"),
        ('all', status.HTTP_401_UNAUTHORIZED, "Token expired")
        ]
    )
async def test_get_transactions(
    data,
    expected_status: int,
    expected_detail: str,
    client: AsyncClient, 
    session_db: AsyncSession
    ):
    id = await session_db.scalar(select(User.id).where(User.email == 'test11@gmail.com'))
    if not id:
        await filling_out_test_willow(session_db)
    id = await session_db.scalar(select(User.id).where(User.email == 'test11@gmail.com'))
    token = await invalid_token(id) if expected_detail == "Token expired" else await valid_token(id)
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get(f"/transactions?data={data}", headers=headers)
    assert response.status_code == expected_status
    if response.status_code == status.HTTP_200_OK:
        assert type(response.json()) == list
        assert response.json()[0]['type'] == 'income' or 'expenses'


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "id_transaction, new_category, new_amount, new_description, expected_status, expected_detail", [
        (1, 'Зарплата', 7777, 'Описание', status.HTTP_200_OK, 'Transaction changed'),
        (1, 'Заработная плата', 7777, 'Описание', status.HTTP_404_NOT_FOUND, 'No such category'),
        (99, 'Зарплата', 7777, 'Описание', status.HTTP_404_NOT_FOUND, 'You do not have such a transaction'),
        (1, 'Зарплата', -7777, 'Описание', status.HTTP_422_UNPROCESSABLE_ENTITY, "Data entered incorrectly"),
        (1, 'Зарплата', 0, 'Описание', status.HTTP_422_UNPROCESSABLE_ENTITY, "Data entered incorrectly")
        ]
    )
async def test_update_transaction(
    id_transaction: int,
    new_category: str,
    new_amount: int,
    new_description: str,
    expected_status: str,
    expected_detail: str,
    client: AsyncClient, 
    session_db: AsyncSession,
    mocker
    ):
    mocker.patch('app.core.tasks.process_task_celery.delay', return_value=True)
    id = await session_db.scalar(select(User.id).where(User.email == 'test11@gmail.com'))
    if not id:
        await filling_out_test_willow(session_db)
    id = await session_db.scalar(select(User.id).where(User.email == 'test11@gmail.com'))
    token = await invalid_token(id) if expected_detail == "Token expired" else await valid_token(id)
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        'id_transaction': id_transaction, 
        'category': new_category, 
        'amount': new_amount,
        'description': new_description
        }
    response = await client.put("/transactions", json=payload, headers=headers)
    assert response.status_code == expected_status
    if response.status_code == 200:
        amount = await session_db.scalar(select(Transaction.amount).where(Transaction.id == 1))
        assert amount == new_amount


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "id_transaction, expected_status, expected_detail", [
        (1, status.HTTP_200_OK, 'Transaction deleted'),
        (99, status.HTTP_404_NOT_FOUND, 'No such transactions'),
        ('invalid', status.HTTP_422_UNPROCESSABLE_ENTITY, "Data entered incorrectly"),
        (1, status.HTTP_401_UNAUTHORIZED, "Token expired")
        ]
    )
async def test_delete_transaction(
    id_transaction: int,
    expected_status: int,
    expected_detail: str,
    client: AsyncClient, 
    session_db: AsyncSession,
    mocker
    ):
    mocker.patch('app.core.tasks.process_task_celery.delay', return_value=True)
    id = await session_db.scalar(select(User.id).where(User.email == 'test11@gmail.com'))
    if not id:
        await filling_out_test_willow(session_db)
    id = await session_db.scalar(select(User.id).where(User.email == 'test11@gmail.com'))
    token = await invalid_token(id) if expected_detail == "Token expired" else await valid_token(id)
    headers = {"Authorization": f"Bearer {token}"}
    data = {'transaction': id_transaction}
    response = await client.request("DELETE", "/transactions", data=data, headers=headers)
    assert response.status_code == expected_status








