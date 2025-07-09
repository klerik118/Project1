from typing import Dict, List, Union
from decimal import Decimal
from json.decoder import JSONDecodeError
import json

from fastapi import APIRouter, Depends, Query, WebSocketDisconnect
from fastapi.websockets import WebSocket, WebSocketState
import aiohttp
import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncio
from pydantic import ValidationError
from redis.asyncio import Redis

from app.core.config import auth
from app.core.database import get_async_session, Transaction, User, get_redis
from app.schemas.user import WsChat


ws_router = APIRouter(tags=['Websocket'])


@ws_router.websocket('/conversion')
async def ws(
    websocket: WebSocket, 
    session_db: AsyncSession = Depends(get_async_session),
    token: str = Query(...)
    ):
    await websocket.accept()
    try:
        payload = jwt.decode(token, auth.public_key_path.read_text(), algorithms=auth.algorithm)
        if payload.get('type') != 'access':
            return await websocket.close(reason='Not аccess token')
        user_id = int(payload.get('sub'))
    except (jwt.PyJWTError, jwt.InvalidTokenError, jwt.DecodeError, jwt.InvalidSignatureError): 
        return await websocket.close(reason='Token error')
    while True:
        q = select(Transaction.amount, Transaction.type).where(Transaction.id_user == user_id)
        query = await session_db.execute(q)
        list_amount = query.mappings().all()
        balance = sum(i.get('amount') if i.get('type') == 'income' else -(i.get('amount')) for i in list_amount)
        async with aiohttp.ClientSession() as session:
                url = f'https://v6.exchangerate-api.com/v6/ed74cdc023db94d33a67cc05/latest/RUB'
                async with session.get(url) as response:
                    result = await response.json()
        result = f"""
RUB = {balance * result['conversion_rates']['RUB']:.2f}
USD = {balance * Decimal(result['conversion_rates']['USD']):.2f}
CNY = {balance * Decimal(result['conversion_rates']['CNY']):.2f}
EUR = {balance * Decimal(result['conversion_rates']['EUR']):.2f}
        """
        await websocket.send_text(result)
        await asyncio.sleep(10)
    

active_connections: List[Dict[str, Union[int, WebSocket]]] = [] 


@ws_router.websocket('/ws-chat')
async def ws_chat(
    websocket: WebSocket, 
    token: str = Query(...), 
    session_db: AsyncSession = Depends(get_async_session),
    redis_app: Redis = Depends(get_redis)
    ):
    await websocket.accept()
    try:
        payload = jwt.decode(token, auth.public_key_path.read_text(), algorithms=auth.algorithm)
        if payload.get('type') != 'access':
            await websocket.send_json({'Error': 'Not eccess token'})
            await websocket.close(reason='Not eccess token') 
            return
        user_id = int(payload.get('sub'))
        active_connections.append({'id': user_id, 'ws': websocket})
        list_users = (await session_db.execute(select(User.id))).scalars().all()
        message_redis = await redis_app.lrange(f'User-{user_id}: message', 0, -1)
        messages = [json.loads(i) for i in message_redis]
        for msg in messages:
            await websocket.send_json(msg)
        await redis_app.delete(f'User-{user_id}: message')
        while True:
            data = (WsChat(**(await websocket.receive_json()))).model_dump()
            if data.get('message') == '':
                await websocket.send_json({'Error': 'Enter message'})
                continue
            elif data.get('group', False) == True:
                for id in [i for i in list_users if i != user_id]:
                    if id in [i['id'] for i in active_connections if i['id'] != user_id]:
                        targ = next((e['ws'] for e in active_connections if e['id'] == id), None)
                        if targ.client_state == WebSocketState.CONNECTED:
                            await targ.send_json({"sender": user_id, "content": data['message']}) 
                        else:
                            msg = {"sender": user_id, "content": data['message']}
                            await redis_app.rpush(f'User-{id}: message', json.dumps(msg))
                    else:
                        msg = {"sender": user_id, "content": data['message']}
                        await redis_app.rpush(f'User-{id}: message', json.dumps(msg))
            elif not data['recipient']: 
                await websocket.send_json({'Error': 'Recipient not entered'})
                continue
            elif not [i for i in data['recipient'] if i in list_users]:
                t = 'No such user'
                await websocket.send_json({'Error': (t + 's') if len(data['recipient']) > 1 else t})
                continue
            else:
                target_users = list(set(data['recipient']))
                for target in target_users:
                    if target not in list_users:
                        await websocket.send_json({'Error': f'No user: {target}'})
                    else:
                        tar = next((i['ws'] for i in active_connections if i['id'] == target), None)
                        if tar and tar.client_state == WebSocketState.CONNECTED:
                            await tar.send_json({"sender": user_id, "content": data['message']})
                        else:
                            msg = {"sender": user_id, "content": data['message']}
                            await redis_app.rpush(f'User-{target}: message', json.dumps(msg))
    except (jwt.PyJWTError, jwt.InvalidTokenError, jwt.DecodeError, jwt.InvalidSignatureError):
        await websocket.send_json({'Error': 'Token error'}) 
        await websocket.close(reason='Token error') 
        return          
    except ValidationError:
        await websocket.send_json({'Error': 'Invalid message format'}) 
    except WebSocketDisconnect:
        index = next((i for i, v in enumerate(active_connections) if v['id'] == user_id), None)
        if index:
            del active_connections[index]
    except JSONDecodeError:
        await websocket.send_json({'Error': 'Invalid json format'}) 


@ws_router.get('/websocket-list')
async def ws_connekt(session_db: AsyncSession = Depends(get_async_session)):
    print(active_connections)
    list_users = (await session_db.execute(select(User.id))).scalars().all()
    return list_users