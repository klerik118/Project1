from fastapi import Depends, Form, Query, status

from app.schemas.user import TransactionCreate, TransactionUpdate, TransacrionsOut, TransactionDepends
from app.repositories.transaction import TransactionRepository
from app.core.config import BaseAppException
from app.core.decorators import TasksRouter


transaction_router = TasksRouter(prefix='/transactions', tags=['Транзакции'])


@transaction_router.post('', response_model=dict)
async def add_new_transaction(transaction: TransactionCreate, d: TransactionDepends = Depends()):
    category = await TransactionRepository.check_category_existence(d.session, d.user_id, transaction.category)
    if not category:
        raise BaseAppException(status_code=status.HTTP_404_NOT_FOUND, message='No such category')
    await TransactionRepository.add_transaction(
        d.session,
        category.id_user, 
        transaction.amount, 
        category.type, 
        transaction.description, 
        category.id
        )
    return {'status': 'Transaction added'}


@transaction_router.get(
        path='', 
        summary='all|one|income|expenses transactions', 
        response_model=list[TransacrionsOut], 
        decorate=False
        ) 
async def get_transactions(
    data: str = Query(..., description='Enter "all" | "income" | "expenses" | id_transaction'),
    d: TransactionDepends = Depends()
    ): 
    if data not in ["all", "income", "expenses"] and not data.isdigit():
        raise BaseAppException(status_code=422, message='Data entered incorrectly!!!!!')
    transactions = await TransactionRepository.all_incom_expenses_one(d.session, d.user_id, data)
    if transactions == []:
        raise BaseAppException(status_code=status.HTTP_404_NOT_FOUND, message='No such transactions')
    list_result = []
    for tran in transactions: 
        tran = dict(tran)    
        tran['date'] = tran.get('date').strftime('%Y-%m-%d %H:%M:%S')
        list_result.append(tran)
    return list_result 


@transaction_router.put('', response_model=dict)
async def update_transaction(transaction: TransactionUpdate, d: TransactionDepends = Depends()):
    if not await TransactionRepository.check_transaction_existence(
        d.session, 
        d.user_id, 
        transaction.id_transaction,
        ):
        raise BaseAppException(status_code=status.HTTP_404_NOT_FOUND, message='You do not have such a transaction')
    category = await TransactionRepository.check_category_existence(d.session, d.user_id, transaction.category)
    if not category:
        raise BaseAppException(status_code=status.HTTP_404_NOT_FOUND, message='No such category')
    await TransactionRepository.update_transaction(
        d.session,
        transaction.id_transaction, 
        category.id, 
        transaction.amount, 
        transaction.description, 
        category.type,
        )
    return {'status': 'Transaction changed'}


@transaction_router.delete('', response_model=dict)
async def delete_transaction(
    transaction: int = Form(..., description='Enter the transaction number you want to delete'),
    d: TransactionDepends = Depends()
    ):   
    if not await TransactionRepository.check_transaction_existence(d.session, d.user_id, transaction):
        raise BaseAppException(status_code=status.HTTP_404_NOT_FOUND, message='No such transactions')
    await TransactionRepository.delete_transaction(d.session, transaction)
    return {'status': f'Transaction № {transaction} deleted'}

