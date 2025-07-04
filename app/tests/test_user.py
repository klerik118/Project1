from unittest.mock import AsyncMock

import pytest
from sqlalchemy.sql import Select, Insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import User
from app.repositories.user import UserRepository


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_id, expected_result, scenario",
    [(42, 42, "existing_user"), (999, None, "non_existing_user")],
    )
async def test_checking_user_id(test_id, expected_result, scenario):
    mock_async_session = AsyncMock(spec=AsyncSession)
    mock_async_session.scalar.return_value = expected_result
    result = await UserRepository.checking_user_id(mock_async_session, id=test_id)
    assert result == expected_result
    mock_async_session.scalar.assert_called_once()
    if expected_result is not None:
        called_query = mock_async_session.scalar.call_args[0][0]
        assert isinstance(called_query, Select)
        assert len(called_query.selected_columns) == 1
        assert called_query.whereclause.compare(User.id == test_id)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exception, match_str, test_id",
    [(Exception("Database error"), "Database error", 42),(ValueError("Invalid user ID"), "Invalid user ID", 0)],
    )
async def test_checking_user_id_errors(exception, match_str, test_id):
    mock_async_session = AsyncMock(spec=AsyncSession)
    mock_async_session.scalar.side_effect = exception
    with pytest.raises(type(exception), match=match_str) as exc_info:
        await UserRepository.checking_user_id(mock_async_session, id=test_id)    
    assert match_str in str(exc_info.value)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "user_id, expected_result, scenario",
    [(1, "user_object", "user_exists"), (2, None, "user_not_found"), (0, None, "invalid_id")],
    )
async def test_get_user_by_id(sample_user, user_id, expected_result, scenario):
    mock_session = AsyncMock(spec=AsyncSession)
    if expected_result == "user_object":
        mock_session.scalar.return_value = sample_user
    else:
        mock_session.scalar.return_value = None
    result = await UserRepository.get_user_by_id(mock_session, user_id)
    if expected_result == "user_object":
        assert isinstance(result, User)
        assert result.id == sample_user.id
    else:
        assert result is None
    mock_session.scalar.assert_called_once()
    called_query = mock_session.scalar.call_args[0][0]
    assert str(called_query.whereclause) == f"users.id = :id_1"
    assert called_query.whereclause.right.value == user_id


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exception, test_id",
    [(Exception("Database error"), 1), (ValueError("Invalid query"), 1)],
    )
async def test_get_user_by_id_errors(exception, test_id):
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.scalar.side_effect = exception
    with pytest.raises(type(exception)) as exc_info:
        await UserRepository.get_user_by_id(mock_session, test_id)
    assert "Database error" or "Invalid query" in str(exc_info.value)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_email, expected_result, scenario",
    [
        ("existing@test.com", "existing@test.com", "email_exists"),
        ("nonexistent@test.com", None, "email_not_found"),
        ("", None, "empty_email"),
        ("invalid-email", None, "invalid_format"),
    ],
)
async def test_checking_user_existence_by_email(test_email, expected_result, scenario):
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.scalar.return_value = expected_result
    result = await UserRepository.сhecking_user_existence_by_email(mock_session, email=test_email)
    assert result == expected_result
    mock_session.scalar.assert_called_once()
    called_query = mock_session.scalar.call_args[0][0]
    assert isinstance(called_query, Select)
    assert len(called_query.selected_columns) == 1
    assert str(called_query.selected_columns[0]) == "users.email"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exception, test_email",
    [
        (Exception("Connection error"), "test@example.com"),
        (ValueError("Invalid query"), "another-test.com"),
    ],
)
async def test_checking_user_existence_by_email_errors(exception, test_email):
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.scalar.side_effect = exception 
    with pytest.raises(type(exception)) as exc_info:
        await UserRepository.сhecking_user_existence_by_email(mock_session, email=test_email)
    assert "Connection error" or "Invalid query" in str(exc_info.value)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "name, email, password, scenario",
    [
        ("John Doe", "john@example.com", "secure123", "valid_data"),
        ("Alice", "alice@test.org", "qwerty", "short_password"),
        ("Bob", "invalid-email", "longpassword", "invalid_email"),
        ("", "empty@name.com", "pass", "empty_name"),
    ],
)
async def test_adding_user(name, email, password, scenario):
    mock_session = AsyncMock(spec=AsyncSession)
    await UserRepository.adding_user(
        session=mock_session,
        name=name,
        email=email,
        hashed_password=password
    )
    mock_session.execute.assert_called_once()
    called_query = mock_session.execute.call_args[0][0]
    assert isinstance(called_query, Insert)
    compiled = called_query.compile()
    assert compiled.params["name"] == name
    assert compiled.params["email"] == email
    assert compiled.params["hashed_password"] == password
    assert str(called_query.table) == "users"
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exception, name, email, password",
    [
        (Exception("DB error"), "John", "john@test.com", "pass123"),
        (ValueError("Invalid data"), "Test", "test@test.com", ""),
    ],
)
async def test_adding_user_errors(exception, name, email, password):
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute.side_effect = exception   
    with pytest.raises(type(exception)) as exc_info:
        await UserRepository.adding_user(session=mock_session, name=name, email=email, hashed_password=password)
    assert "DB error" or "Invalid data" in str(exc_info)     
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_email, expected_result, scenario",
    [
        ("test@example.com", "user_object", "email_exists"),
        ("nonexistent@test.com", None, "email_not_found"),
        ("", None, "empty_email"),
        ("invalid-format", None, "invalid_email"),
    ],
)
async def test_get_user_by_email(sample_user, test_email, expected_result, scenario):
    mock_session = AsyncMock(spec=AsyncSession)
    if expected_result == "user_object":
        mock_session.scalar.return_value = sample_user
    else:
        mock_session.scalar.return_value = None
    result = await UserRepository.get_user_by_email(mock_session, test_email)
    if expected_result == "user_object":
        assert isinstance(result, User)
        assert result.email == test_email
    else:
        assert result is None
    mock_session.scalar.assert_called_once()
    called_query = mock_session.scalar.call_args[0][0]
    assert called_query.whereclause.compare(User.email == test_email)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exception, test_email",
    [
        (Exception("Database error"), "error@test.com"),
        (ValueError("Invalid query"), "invalid@test.com"),
    ],
)
async def test_get_user_by_email_errors(exception, test_email):
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.scalar.side_effect = exception
    with pytest.raises(type(exception)) as exc_info:
        await UserRepository.get_user_by_email(mock_session, test_email)
    assert "Database error" or "Invalid data" in str(exc_info)     
    mock_session.commit.assert_not_called()

        