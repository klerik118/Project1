import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from decimal import Decimal
from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import Category, Transaction
from app.repositories.transaction import TransactionRepository


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "user_id, category_name, mock_return, expected_result, scenario",
    [
        (
            1,
            "Food",
             Category(id=1, name="Food", type="expense", description="Test", id_user=1),
            {"id": 1, "name": "Food", "type": "expense", "description": "Test", "id_user": 1},
            "Existing category"
        ),
        (
            2,
            "Transport",
            None,
            None,
            "Non-existent category"
        ),
        (
            3,
            "Entertainment",
            None,
            None,
            "Category belongs to another user"
        ),
    ]
)
async def test_check_category_existence(user_id, category_name, mock_return, expected_result, scenario):
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.scalar.return_value = mock_return
    result = await TransactionRepository.check_category_existence(
        session=mock_session,
        user_id=user_id,
        category_name=category_name
    )
    if expected_result is None:
        assert result is None, f"Expected None for scenario: {scenario}"
    else:
        assert result is not None, f"Expected category for scenario: {scenario}"
        assert result.id == expected_result["id"]
        assert result.name == expected_result["name"]
        assert result.id_user == expected_result["id_user"]


@pytest.mark.asyncio
async def test_check_category_existence_with_exception():
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.scalar.side_effect = Exception("DB error")
    with pytest.raises(Exception, match="DB error") as exc_info:
        await TransactionRepository.check_category_existence(
            session=mock_session,
            user_id=1,
            category_name="Food"
        )
    assert "DB error" in str(exc_info.value)

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "id_user, amount, type, description, category_id, expected_values",
    [
        (
            1, 
            Decimal("100.50"), 
            "income", 
            "Salary", 
            5,
            {
                "id_user": 1,
                "amount": Decimal("100.50"),
                "type": "income",
                "description": "Salary",
                "id_category": 5,
            }
        ),
        (
            2, 
            Decimal("50.00"), 
            "expense", 
            "", 
            3,
            {
                "id_user": 2,
                "amount": Decimal("50.00"),
                "type": "expense",
                "description": "",
                "id_category": 3,
            }
        ),
        (
            3, 
            Decimal("200.00"), 
            "income", 
            "Bonus", 
            None,
            {
                "id_user": 3,
                "amount": Decimal("200.00"),
                "type": "income",
                "description": "Bonus",
                "id_category": None,
            }
        ),
    ]
)
async def test_add_transaction(id_user, amount, type, description, category_id, expected_values):
    mock_session = AsyncMock()
    mock_session.execute.return_value = None
    await TransactionRepository.add_transaction(
        session=mock_session,
        id_user=id_user,
        amount=amount,
        type=type,
        description=description,
        category_id=category_id
    )
    assert mock_session.execute.call_count == 1
    called_query = mock_session.execute.call_args[0][0]
    assert str(called_query.table) == str(Transaction.__table__)
    compiled = called_query.compile()
    assert compiled.params["id_user"] == expected_values["id_user"]
    assert compiled.params["amount"] == expected_values["amount"]
    assert compiled.params["type"] == expected_values["type"]
    assert compiled.params["description"] == expected_values["description"]
    assert compiled.params["id_category"] == expected_values["id_category"]
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("user_id, input_data, expected_query, expected_result, expected_exception", [
    (1, 'all',None,
        [{
                'id': 1,
                'name': 'Salary',
                'type': 'income',
                'amount': Decimal('1000.00'),
                'date': datetime(2023, 1, 1),
                'description': 'Monthly salary'
            }],None),
    (2, 'income', None,[{
                'id': 2,
                'name': 'Salary',
                'type': 'income',
                'amount': Decimal('1500.00'),
                'date': datetime(2023, 1, 2),
                'description': 'Bonus'
            }], None),
    (3, 'expenses', None,[{
                'id': 3,
                'name': 'Food',
                'type': 'expenses',
                'amount': Decimal('50.00'),
                'date': datetime(2023, 1, 3),
                'description': 'Groceries'
            }], None),
    (4, '123', None, [{
                'id': 123,
                'name': 'Rent',
                'type': 'expenses',
                'amount': Decimal('500.00'),
                'date': datetime(2023, 1, 4),
                'description': 'Monthly rent'
            }],None),
])
async def test_all_incom_expenses_one(user_id, input_data, expected_query, expected_result, expected_exception):
    mock_session = AsyncMock()
    if expected_exception:
        with pytest.raises(expected_exception) as exc_info:
            await TransactionRepository.all_incom_expenses_one(mock_session, user_id, input_data)
    else:
        mock_result = MagicMock()
        mock_mappings = MagicMock()
        mock_mappings.all.return_value = expected_result
        mock_result.mappings.return_value = mock_mappings
        mock_session.execute.return_value = mock_result
        result = await TransactionRepository.all_incom_expenses_one(mock_session, user_id, input_data)
        assert result == expected_result
        assert mock_session.execute.called
        if expected_query:
            called_query = mock_session.execute.call_args[0][0]
            assert str(called_query) == str(expected_query)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "user_id,transaction_id,expected_result,mock_return",
    [
        (1, 1, 1, 1),  
        (1, 2, None, None),  
        (2, 1, None, None),  
    ]
)
async def test_check_transaction_existence(user_id, transaction_id, expected_result, mock_return):
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.scalar.return_value = mock_return
    result = await TransactionRepository.check_transaction_existence(
        session=mock_session,
        user_id=user_id,
        transaction_id=transaction_id
    )
    assert result == expected_result
    mock_session.scalar.assert_called_once()
    called_query = mock_session.scalar.call_args[0][0]
    assert called_query.whereclause.compare(
        (Transaction.id_user == user_id) & (Transaction.id == transaction_id)
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "id_transaction, category_id, new_amount, new_description, category_type, expected_exception, exc_message",
    [
        (1, 5, Decimal("100.50"), "Food expenses", "expense", None, None),
        (2, 3, Decimal("2000.00"), "Salary income", "income", None, None),
        (3, None, Decimal("50.25"), "Miscellaneous", "expense", None, None),
        (4, 5, Decimal("100.50"), "Food expenses", "expense", SQLAlchemyError, "Database error"),
        (5, 3, "not_a_number", "Salary income", "income", TypeError, None),
    ],
)
async def test_update_transaction(
    id_transaction, 
    category_id, 
    new_amount, 
    new_description, 
    category_type,
    expected_exception,
    exc_message
):
    mock_session = AsyncMock()
    if expected_exception:
        if exc_message:
            exception = expected_exception(exc_message)
            mock_session.execute.side_effect = exception
            mock_session.commit.side_effect = exception
            with pytest.raises(expected_exception) as exc_info:
                await TransactionRepository.update_transaction(
                    session=mock_session,
                    id_transaction=id_transaction,
                    category_id=category_id,
                    new_amount=new_amount,
                    new_description=new_description,
                    category_type=category_type,
                )
        else:
            mock_session.execute.side_effect = expected_exception
            with pytest.raises(expected_exception):
                await TransactionRepository.update_transaction(
                    session=mock_session,
                    id_transaction=id_transaction,
                    category_id=category_id,
                    new_amount=new_amount,
                    new_description=new_description,
                    category_type=category_type,
                )
    else:
        mock_result = AsyncMock()
        mock_session.execute.return_value = mock_result
        await TransactionRepository.update_transaction(
            session=mock_session,
            id_transaction=id_transaction,
            category_id=category_id,
            new_amount=new_amount,
            new_description=new_description,
            category_type=category_type,
        )
        mock_session.execute.assert_called_once()
        args, _ = mock_session.execute.call_args


        called_query = mock_session.execute.call_args[0][0]
        assert str(called_query.table) == "transactions"
        assert called_query.whereclause.right.value == id_transaction
        compiled = called_query.compile()
        assert compiled.params["id_category"] == category_id
        assert compiled.params["description"] == new_description
        assert compiled.params["type"] == category_type
        if isinstance(new_amount, Decimal):
            assert str(compiled.params["amount"]) == str(new_amount)
        else:
            assert compiled.params["amount"] == new_amount
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("transaction_id, expected_exception, commit_called", [
    (1, None, True),
    (999, None, True),
    (0, ValueError, False),  
    (2, SQLAlchemyError, False), 
    (3, Exception, False),  
    ], ids=[
    "success_delete",
    "delete_non_existing",
    "invalid_id",
    "db_error",
    "generic_error"
    ])
async def test_delete_transaction_error(transaction_id,  expected_exception,  commit_called):
    mock_session = AsyncMock(spec=AsyncSession)
    if expected_exception == SQLAlchemyError:
        mock_session.execute.side_effect = SQLAlchemyError("DB error")
    elif expected_exception == ValueError:
        mock_session.execute.side_effect = ValueError("Invalid ID")
    elif expected_exception == Exception:
        mock_session.execute.side_effect = Exception("Unexpected error")
    if expected_exception:
        with pytest.raises(expected_exception):
            await TransactionRepository.delete_transaction(mock_session, transaction_id)
    else:
        await TransactionRepository.delete_transaction(mock_session, transaction_id)
    assert mock_session.commit.called == commit_called



