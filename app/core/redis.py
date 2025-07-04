import json
from typing import Optional

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.repositories.category import CategoryRepository
from app.core.config import BaseAppException
from app.core.config import redis_expire


async def redis_update_categories(session: AsyncSession, redis_app: Redis, user_id: int) -> Optional[list]:
    categories = await CategoryRepository.get_categories(session, user_id)
    if not categories:
        raise BaseAppException(status_code=status.HTTP_404_NOT_FOUND, message='No categories')
    categories_dict = [{
        "id_user": cat.id_user,
        'id': cat.id,
        "name": cat.name,
        "type": cat.type,
        "description": cat.description,
        }for cat in categories]
    await redis_app.setex(f'Categories user_id: {user_id}', redis_expire, json.dumps(categories_dict))
    return categories