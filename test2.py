from pydantic import BaseModel, ValidationError
from typing import List
import redis
import asyncio
import json

s = {"recipient": [], "message": 'text'}  #, "group": True

class WsChat(BaseModel):
    recipient: List[int]
    message: str
    group: bool = False


from redis.asyncio import Redis

from app.core.database import get_redis


red = redis.Redis('localhost', decode_responses=True)  #'redis://redis:6379'

#red.rpush('hi', json.dumps({"sender": 1, "content": "by"}))

msg = red.lrange('hi', 0, -1)

print([json.loads(i) for i in msg])


#r = redis.Redis(host='redis', port=6379)

#r.rpush('hi', 'heloo')