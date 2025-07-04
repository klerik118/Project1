from celery import Celery


celery_app = Celery(
    'worker', 
    broker='redis://redis:6379/1', 
    backend='redis://redis:6379/1', 
    include=['app.core.tasks']
    )


celery_app.conf.update(
    task_serializer='json',  
    accept_content=['json'], 
    result_serializer='json', 
    timezone='Europe/Moscow', 
    enable_utc=True
    )

