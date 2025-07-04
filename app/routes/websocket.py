from typing import Dict, List, Union
from decimal import Decimal
import re
from json.decoder import JSONDecodeError

from fastapi import APIRouter, Depends, Query, WebSocketDisconnect
from fastapi.websockets import WebSocket
import aiohttp
import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncio

from app.core.config import auth
from app.core.database import get_async_session, Transaction


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
    

active_connections: List[Dict[str, Union[int, WebSocket]]] = [] #


@ws_router.websocket('/ws-chat')
async def ws_chat(websocket: WebSocket, token: str = Query(...)):
    await websocket.accept()
    try:
        payload = jwt.decode(token, auth.public_key_path.read_text(), algorithms=auth.algorithm)
        if payload.get('type') != 'access':
            await websocket.close(reason='Not eccess token') 
            return
        user_id = int(payload.get('sub'))
    except (jwt.PyJWTError, jwt.InvalidTokenError, jwt.DecodeError, jwt.InvalidSignatureError) as err:
        await websocket.close(reason='Token error') 
        return
    active_connections.append({'id': user_id, 'ws': websocket})
    while True:
        try:
            data = await websocket.receive_json()
            message = data.get('message', None)
            group = data.get('group', None)
            if group == True and isinstance(message, str):
                group_chat = [conn['ws'] for conn in active_connections if conn['id'] != user_id]
                for chat in group_chat:
                    await chat.send_json({"sender": user_id, "content": message})
            else:
                target_user_id = data.get('recipient', None)       
                if (not (target_user_id and message) or 
                    not (isinstance(target_user_id, list) and isinstance(message, str))):
                    await websocket.send_json({'Error': 'Invalid message format'})
                    continue
                #target_user = next((conn['ws'] for conn in active_connections if conn['id'] == target_user_id), None)
                target_user = [conn['ws'] for conn in active_connections if conn['id'] in target_user_id]
                if not target_user: 
                    await websocket.send_json({'Error': 'No such user'})
                    continue
                for tar in target_user:
                    await tar.send_json({"sender": user_id, "content": message})
        except WebSocketDisconnect:
            del active_connections[user_id]  
            await websocket.send_json({'Error': 'No such user'}) 
        except JSONDecodeError:
            await websocket.send_json({'Error': 'Invalid json format'}) 


@ws_router.get('/websocket-list')
async def ws_connekt():
    print(active_connections)
    return [conn['id'] for conn in active_connections]