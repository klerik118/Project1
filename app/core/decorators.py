from typing import Callable, Any, Coroutine
from functools import wraps
from fastapi import Depends, APIRouter

from app.schemas.user import CategoryDepends, TransactionDepends
from app.core.redis import redis_update_categories
from app.core.tasks import process_task_celery


def update_redis_cache(func: Callable[..., Coroutine[Any, Any, dict]]):
    @wraps(func)
    async def wrapper(*args, d: CategoryDepends = Depends(), **kwargs):
        result = await func(*args, d=d, **kwargs)
        if await d.redis_app.get(f'Categories user_id: {d.user_id}'): 
            await redis_update_categories(d.session, d.redis_app, d.user_id)
        return result
    return wrapper


class TasksRouter(APIRouter):

    def add_api_route(self, path: str, endpoint: Callable, decorate: bool = True, **kwargs):
        print(decorate)
        if decorate:
            @wraps(endpoint)
            async def wrapped_endpoint(d: TransactionDepends = Depends(), *args, **kwargs):
                result = await endpoint(d=d, *args, **kwargs)
                process_task_celery.delay(d.user_id)
                return result
            endpoint_to_use = wrapped_endpoint
        else:
            endpoint_to_use = endpoint
        super().add_api_route(path, endpoint_to_use, **kwargs)

    def get(self, path: str, *, decorate: bool = True, **kwargs: Any,) -> Callable:
        def decorator(func: Callable):
            self.add_api_route(path, func, decorate=decorate, methods=["GET"], **kwargs)
            return func
        return decorator        