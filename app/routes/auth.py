from datetime import datetime, timezone, timedelta

import jwt
from fastapi import APIRouter, Depends, status, Query
from passlib.hash import pbkdf2_sha256   
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.schemas.user import UserCreate, UserLogin, UserOut, UserOutId
from app.core.security import token_verification, get_id_current_user
from app.repositories.user import UserRepository
from app.core.config import auth, BaseAppException, redis_expire
from app.core.database import get_async_session, get_redis


user_router = APIRouter(tags=['Registration/Authorization'])


@user_router.post('/registration', summary='Registration', response_model=dict)
async def add_user(new_user: UserCreate, session: AsyncSession = Depends(get_async_session)):
    user = await UserRepository.сhecking_user_existence_by_email(session, new_user.email)
    if user:
        raise BaseAppException(
            status_code=status.HTTP_401_UNAUTHORIZED,  
            message='A user with this email is already registered'
            )
    hashed_password = pbkdf2_sha256.hash(new_user.password)
    await UserRepository.adding_user(session, new_user.name, new_user.email, hashed_password)
    return {'status': f'User with email {new_user.email} successfully added'}


@user_router.post('/login', summary='Login', response_model=dict) 
async def user_login(user: UserLogin, session: AsyncSession = Depends(get_async_session)):#respons: Response, 
    user_db = await UserRepository.get_user_by_email(session, user.email)
    if not user_db:
        raise BaseAppException(status_code=status.HTTP_401_UNAUTHORIZED, message='Not surch user')
    if user.email == user_db.email and pbkdf2_sha256.verify(user.password, user_db.hashed_password):
        private_key = auth.private_key_path.read_text()  
        expire = datetime.now(timezone.utc) + timedelta(minutes=auth.expiration)
        refresh_expire = datetime.now(timezone.utc) + timedelta(days=auth.expiration)
        payload = {"sub": str(user_db.id), "exp": expire, 'type': 'access'}
        encode_jwt = jwt.encode(payload, private_key, algorithm=auth.algorithm)
        refresh_payload = {"sub": str(user_db.id), "exp": refresh_expire, 'type': 'refresh'}
        refresh_token = jwt.encode(refresh_payload, private_key, algorithm=auth.algorithm)
        #respons.set_cookie(key='eccess_token', value=encode_jwt, samesite='None', httponly=True, secure=False, domain='localhost')
        return {'eccess_token': encode_jwt, 'refresh_token': refresh_token}       
    raise BaseAppException(status_code=status.HTTP_401_UNAUTHORIZED, message='Invalid password')
     

@user_router.get('/user-info', summary='User information', response_model=UserOut)
async def get_user_data(
    redis_app: Redis = Depends(get_redis),
    user_id: UserOutId = Depends(get_id_current_user),
    session: AsyncSession = Depends(get_async_session)
    ):
    user_info_from_redis = await redis_app.hgetall(f'User information: {user_id}')
    if user_info_from_redis:
        return user_info_from_redis
    else:
        user = await UserRepository.get_user_by_id(session, user_id)
        user.date_registration = user.date_registration.strftime('%Y-%m-%d %H:%M:%S')
        await redis_app.hset(f'User information: {user.id}', mapping={
            'id': user.id,
            'name': user.name, 
            'email': user.email, 
            'date_registration': user.date_registration
            })
        await redis_app.expire(f'User information: {user_id}', redis_expire)
        return user
                     

@user_router.get('/refresh-token', summary='Refresh token', response_model=dict)
async def refresh_token(id_user: str = Depends(token_verification)):
    private_key = auth.private_key_path.read_text()  
    expire = datetime.now(timezone.utc) + timedelta(minutes=auth.expiration)
    payload = {"sub": str(id_user), "exp": expire, 'type': 'access'}
    encode_jwt = jwt.encode(payload, private_key, algorithm=auth.algorithm)
    return {'access token': encode_jwt}


"""
@user_router.websocket('/ws')
async def ws(
    websocket: WebSocket, 
    session_db: AsyncSession = Depends(get_async_session),
    token: str = Query(...)
    ):
    await websocket.accept()
    try:
        payload = jwt.decode(token, auth.public_key_path.read_text(), algorithms=auth.algorithm)
        if payload.get('type') != 'access':
            await websocket.close(code=1011, reason='Not eccess token') #
            return
        user_id = int(payload.get('sub'))
    except (jwt.PyJWTError, jwt.InvalidTokenError, jwt.DecodeError, jwt.InvalidSignatureError) as err: #Exception, 
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason='Token error') #
        return
    while True:
        q = select(Transaction.amount, Transaction.type).where(Transaction.id_user == user_id)
        query = await session_db.execute(q)
        list_amount = query.mappings().all()
        balance = sum(i.get('amount') if i.get('type') == 'income' else -(i.get('amount')) for i in list_amount)
        async with aiohttp.ClientSession() as session:
                url = f'https://v6.exchangerate-api.com/v6/ed74cdc023db94d33a67cc05/latest/RUB'
                async with session.get(url) as response:
                    result = await response.json()
        result = f'''RUB = {balance * result['conversion_rates']['RUB']:.2f}
USD = {balance * Decimal(result['conversion_rates']['USD']):.2f}
CNY = {balance * Decimal(result['conversion_rates']['CNY']):.2f}
EUR = {balance * Decimal(result['conversion_rates']['EUR']):.2f}'''
        await websocket.send_text(result)
        await asyncio.sleep(10)


active_connections: Dict[int, WebSocket] = {}


@user_router.websocket('/ws-chat')
async def ws_chat(websocket: WebSocket, token: str = Query(...)):
    await websocket.accept()
    try:
        payload = jwt.decode(token, auth.public_key_path.read_text(), algorithms=auth.algorithm)
        if payload.get('type') != 'access':
            await websocket.close(code=1011, reason='Not eccess token') 
            return
        user_id = int(payload.get('sub'))
    except (jwt.PyJWTError, jwt.InvalidTokenError, jwt.DecodeError, jwt.InvalidSignatureError) as err:
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason='Token error') 
        return
    active_connections[user_id] = websocket
    while True:
        try:
            data = await websocket.receive_text()
            target_user_id = data[0]
            message = data[2:]
            if target_user_id.isdigit() != True or not target_user_id or not message:
                await websocket.send_text('Invalid message format')
                continue
            target_user = active_connections.get(int(target_user_id), None)
            if not target_user: # or target_user.client_state != WebSocketState.CONNECTED
                await websocket.send_text('No such user')
                continue
            await target_user.send_text(f'({user_id}): {message}')
        except WebSocketDisconnect:
            del active_connections[user_id]  
            await websocket.send_text('No such user')    
            

@user_router.get('/websocket')
async def ws_connekt(): #user_id: UserOutId = Depends(get_id_current_user)
    print(active_connections)
"""



    
    

