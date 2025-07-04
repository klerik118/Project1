from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import and_
from sqlalchemy.sql import Select, Insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from passlib.hash import pbkdf2_sha256 
from sqlalchemy import select, insert

from app.core.database import Category,User
from app.repositories.category import CategoryRepository


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "user_id, category_name, expected_result, scenario",
    [
        (1, "Food", "Food", "category_exists"),
        (1, "Nonexistent", None, "category_not_found"),
        (2, "Food", None, "wrong_user_id"),
        (None, "Food", None, "null_user_id"),
        (1, "", None, "empty_category_name"),
    ],
)
async def test_get_category(sample_category, user_id, category_name, expected_result, scenario):
    mock_session = AsyncMock(spec=AsyncSession)
    if expected_result:
        mock_session.scalar.return_value = sample_category["name"]
    else:
        mock_session.scalar.return_value = None
    result = await CategoryRepository.get_category(
        session=mock_session, 
        user_id=user_id, 
        name_category=category_name
        )
    assert result == expected_result
    mock_session.scalar.assert_called_once()
    called_query = mock_session.scalar.call_args[0][0]
    assert isinstance(called_query, Select)
    expected_where = and_(Category.id_user == user_id, Category.name == category_name)
    where_clauses = called_query.whereclause
    assert where_clauses.compare(expected_where)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exception, user_id, category_name",
    [
        (Exception("Database error"), 1, "Food"),
        (ValueError("Invalid query"), 1, "Invalid#Name"),
    ],
)
async def test_get_category_errors(exception, user_id, category_name):
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.scalar.side_effect = exception
    with pytest.raises(type(exception)) as exc_info:
        await CategoryRepository.get_category(session=mock_session, user_id=user_id, name_category=category_name)
    assert str(exc_info.value) == str(exception)
    mock_session.commit.assert_not_called()

    
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "name, type, description, user_id, scenario",
    [
        ("Food", "expense", "Groceries", 1, "valid_data"),
        ("Salary", "income", "Monthly salary", 2, "income_category"),
        ("", "expense", "No name", 3, "empty_name"),
        ("Entertainment", "expense", "", 5, "empty_description"),
        ("Long name"*10, "expense", "Very long name", 6, "long_name"),
    ],
)
async def test_create_new_category(name, type, description, user_id, scenario):
    mock_session = AsyncMock(spec=AsyncSession)
    await CategoryRepository.create_new_category(
        session=mock_session,
        name=name,
        type=type,
        description=description,
        user_id=user_id
    )
    mock_session.execute.assert_called_once()
    called_query = mock_session.execute.call_args[0][0]
    assert isinstance(called_query, Insert)
    assert str(called_query.table) == "categories"
    compiled = called_query.compile()
    assert compiled.params["name"] == name
    assert compiled.params["type"] == type
    assert compiled.params["description"] == description
    assert compiled.params["id_user"] == user_id
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exception, name, type, description, user_id",
    [
        (Exception("DB error"), "Test", "expense", "Desc", 1),
        (ValueError("Invalid type"), "Test", "invalid", "Desc", 1),
    ],
)
async def test_create_new_category_errors(exception, name, type, description, user_id):
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute.side_effect = exception 
    with pytest.raises(exception.__class__) as exc_info:
        await CategoryRepository.create_new_category(
            session=mock_session,
            name=name,
            type=type,
            description=description,
            user_id=user_id
        )
    assert str(exc_info.value) == str(exception)
    mock_session.commit.assert_not_called()
    

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "user_id, expected_count, scenario",
    [
        (1, 2, "user_has_categories"),
        (2, 0, "user_has_no_categories"),
        (None, 0, "null_user_id"),
    ],
)
async def test_get_categories(sample_categories, user_id, expected_count, scenario): 
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    if expected_count > 0:
        mock_result.scalars.return_value.all.return_value = sample_categories
    else:
        mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result
    result = await CategoryRepository.get_categories(mock_session, user_id)
    if expected_count > 0:
        assert len(result) == expected_count
    else:
        assert result == []
    mock_session.execute.assert_called_once()
    called_query = mock_session.execute.call_args[0][0]
    assert isinstance(called_query, Select)
    assert str(called_query.whereclause.left) == "categories.id_user"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exception, user_id",
    [
        (Exception("Database error"), 1),
        (ValueError("Invalid user_id"), -1),
    ],
)
async def test_get_categories_errors(exception, user_id):
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute.side_effect = exception
    with pytest.raises(exception.__class__) as exc_info:
        await CategoryRepository.get_categories(mock_session, user_id)
    assert str(exc_info.value) == str(exception)
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "category_id, user_id, expected_result, scenario",
    [
        (1, 1, 1, "valid_category_and_user"),
        (1, 2, None, "wrong_user"),
        (999, 1, None, "non_existent_category"),
        (None, 1, None, "null_category_id"),
        (1, None, None, "null_user_id"),
    ],
)
async def test_get_category(category_id, user_id, expected_result, scenario):
    mock_session = AsyncMock()
    if expected_result is not None:
        mock_session.scalar.return_value = expected_result
    else:
        mock_session.scalar.return_value = None
    result = await CategoryRepository.get_category(mock_session, category_id, user_id)
    assert result == expected_result
    assert mock_session.scalar.called
    called_query = mock_session.scalar.call_args[0][0]
    assert isinstance(called_query, Select)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exception, user_id, category_id",
    [
        (Exception("Database error"), 1, 1),
        (ValueError("Invalid query"), 1, "1"),
    ],
)
async def test_get_category_errors(exception, user_id, category_id):
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.scalar.side_effect = exception
    with pytest.raises(type(exception)) as exc_info:
        await CategoryRepository.get_category(
            session=mock_session,
            user_id=user_id,
            category_id=category_id
        ) 
    assert str(exc_info.value) == str(exception)
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "category_id, name, type, description, should_raise, scenario",
    [
        (1, "New Name", "expense", "New description", False, "valid_update"),
        (2, "Other", "income", "", False, "empty_description"),
        (1, "", "expense", "Desc", False, "empty_name"),
        (1, "Name", "expense", None, False, "null_description"),
        (1, "Name", "expense", "Desc", True, "db_error"),
        (None, "Name", "expense", "Desc", True, "null_category_id"),
    ],
)
async def test_update_category(
    category_id: int,
    name: str,
    type: str,
    description: str,
    should_raise: bool,
    scenario: str
):
    mock_session = AsyncMock()
    if should_raise:
        if category_id is None:
            mock_session.execute.side_effect = ValueError("Invalid category_id")
        else:
            mock_session.execute.side_effect = SQLAlchemyError("DB error")
            mock_session.commit.side_effect = SQLAlchemyError("Commit failed")
    else:
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result
    if should_raise:
        with pytest.raises((SQLAlchemyError, ValueError)):
            await CategoryRepository.update_category(
                mock_session, category_id, name, type, description
            )
    else:
        await CategoryRepository.update_category(
            mock_session, category_id, name, type, description
        )
    if not should_raise:
        assert mock_session.execute.called
        called_query = mock_session.execute.call_args[0][0]
        assert str(called_query.table) == "categories"
        assert str(called_query.whereclause.left) == "categories.id"
        assert called_query.whereclause.right.value == category_id
        compiled = called_query.compile()
        assert compiled.params["name"] == name
        assert compiled.params["type"] == type
        if description is not None:
            assert compiled.params["description"] == description
        assert mock_session.commit.called


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "category_id, mock_rowcount, should_raise, scenario",
    [
        (1, 1, False, "successful_delete"),
        (2, 1, False, "another_successful_delete"),
        (999, 0, False, "non_existent_category"),
        (1, 0, True, "db_execute_error"),
        (1, 1, True, "db_commit_error"),
        (None, 0, True, "null_category_id"),
    ],
)
async def test_delete_category(
    category_id: int,
    mock_rowcount: int,
    should_raise: bool,
    scenario: str
):
    mock_session = AsyncMock()
    if should_raise:
        if scenario == "db_execute_error":
            mock_session.execute.side_effect = SQLAlchemyError("Execute failed")
        elif scenario == "db_commit_error":
            mock_result = MagicMock()
            mock_result.rowcount = mock_rowcount
            mock_session.execute.return_value = mock_result
            mock_session.commit.side_effect = SQLAlchemyError("Commit failed")
        else:  
            mock_session.execute.side_effect = ValueError("Invalid category_id")
    else:
        mock_result = MagicMock()
        mock_result.rowcount = mock_rowcount
        mock_session.execute.return_value = mock_result
    if should_raise:
        with pytest.raises((SQLAlchemyError, ValueError)):
            await CategoryRepository.delete_category(mock_session, category_id)
    else:
        await CategoryRepository.delete_category(mock_session, category_id)
    if not should_raise:
        assert mock_session.execute.called
        called_query = mock_session.execute.call_args[0][0]   
        assert str(called_query.table) == "categories"
        assert str(called_query.whereclause.left) == "categories.id"
        assert called_query.whereclause.right.value == category_id
        assert mock_session.commit.called
    else:
        if scenario == "db_commit_error":
            assert mock_session.execute.called


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'user_id, expected_detail', [(5, 'valid_id'),(99, 'invalid_id'), (1, 'Database error')]
    )
async def test_list_name_existing_categories(
    user_id: int,
    expected_detail: str,
    session_db: AsyncSession,
    mocker
    ):
    id = await session_db.scalar(select(User.id).where(User.email == 'test101@email.ru'))
    if not id:
        hashed_password=pbkdf2_sha256.hash('password')
        query = insert(User).values(name='test_name', email='test101@email.ru', hashed_password=hashed_password)
        await session_db.execute(query)
        await session_db.commit()
        id = await session_db.scalar(select(User.id).where(User.email == 'test101@email.ru'))
        test_categories = [
                {'name': 'Заработок', 'type': 'income', 'description': 'Описание'},
                {'name': 'Бытовые расходы', 'type': 'expenses', 'description': 'Описание'}
                ]
        for category in test_categories:
            query = insert(Category).values(
                name=category['name'], 
                type=category['type'], 
                description=category['description'], 
                id_user=id,
                )
            await session_db.execute(query)
            await session_db.commit()
    if expected_detail == 'Database error':
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=Exception('Database error'))
        with pytest.raises(Exception):
            await CategoryRepository.list_name_existing_categories(mock_session, user_id)
    result = await CategoryRepository.list_name_existing_categories(session_db, user_id)
    if expected_detail == 'valid_id':
        assert sorted(result) == ['Бытовые расходы', 'Заработок']
    else: 
        assert result == []