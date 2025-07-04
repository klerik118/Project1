from typing import Dict
import json

from fastapi import APIRouter, Depends, Body, status

from app.schemas.user import CategoryCreate, UpdateCategory, CategoryOut, CategoryDepends
from app.repositories.category import CategoryRepository
from app.core.config import BaseAppException
from app.core.redis import redis_update_categories
from app.core.decorators import update_redis_cache


category_router = APIRouter(prefix='/categories', tags=['Categories'])#


@category_router.post('', summary='creating a category', response_model=dict)
@update_redis_cache
async def add_category(category: CategoryCreate, d: CategoryDepends = Depends()):
    if await CategoryRepository.get_name_category(d.session, d.user_id, category.name):
        raise BaseAppException(status_code=status.HTTP_403_FORBIDDEN, message='This category already exists')
    await CategoryRepository.create_new_category(
        d.session, 
        category.name, 
        category.type, 
        category.description, 
        d.user_id,
        )
    return {"status": f"Category {category.name} successfully added"}


@category_router.get('', summary='get all categories', response_model=list[CategoryOut])
async def get_all_categories(d: CategoryDepends = Depends()):
    categories_from_redis = await d.redis_app.get(f'Categories user_id: {d.user_id}')
    if not categories_from_redis:
        categories_from_db = await redis_update_categories(d.session, d.redis_app, d.user_id)
        return categories_from_db
    return json.loads(categories_from_redis)
    
  
@category_router.put('', summary='change category', response_model=dict)
@update_redis_cache
async def update_category(category: UpdateCategory, d: CategoryDepends = Depends()):
    category_db = await CategoryRepository.get_category(d.session, category.id, d.user_id)
    if not category_db:
        raise BaseAppException(status_code=status.HTTP_404_NOT_FOUND, massage='No such category')
    list_existing_categories = await CategoryRepository.list_name_existing_categories(d.session, d.user_id)
    if category.new_name != category_db.name and category.new_name in list_existing_categories:
        raise BaseAppException(status_code=status.HTTP_404_NOT_FOUND, message='such a category already exists')
    await CategoryRepository.update_category(
        d.session, 
        category.id, 
        category.new_name, 
        category.new_type_category, 
        category.new_description,
        )
    return {"status": "Category changed"}


@category_router.delete('', summary='delete category', response_model=dict)
@update_redis_cache
async def delete_category(category: Dict[str, int] = Body({'id': 0}), d: CategoryDepends = Depends()):
    if not await CategoryRepository.get_category(d.session, category.get('id'), d.user_id):
        raise BaseAppException(status_code=status.HTTP_404_NOT_FOUND, message='No such category')
    await CategoryRepository.delete_category(d.session, category.get('id'))
    return {"status": f'Category № {category.get('id')} deleted'}
