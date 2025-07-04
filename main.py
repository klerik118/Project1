from fastapi import FastAPI, Request, status, Response
from fastapi.responses import JSONResponse
import json
import jwt

from app.routes.auth import user_router
from app.routes.transactions import transaction_router
from app.routes.categories import category_router
from app.routes.websocket import ws_router
from app.core.config import logger, BaseAppException, auth


app = FastAPI(title="Financial management")


@app.middleware('http')
async def log_requests(request: Request, call_next):
    auth_header = request.headers.get('Authorization')
    id_user = None
    if auth_header and auth_header.startswith('Bearer'):
        token = auth_header.split(' ')[1]
        try:
            decod = jwt.decode(token, auth.public_key_path.read_text(), auth.algorithm)
            id_user = decod.get('sub')  
        except (jwt.ExpiredSignatureError, jwt.PyJWTError):
            try:
                decod = jwt.decode(
                    token, 
                    auth.public_key_path.read_text(), 
                    auth.algorithm, 
                    options={'verify_exp': False}
                    )
                id_user = decod.get('sub')  
            except jwt.PyJWTError:
                pass
    if request.method in ("POST", "PUT", "DELETE"):
        body = await request.body()
        async def restore_body():
            yield body
        request._stream = restore_body()
        try:
            content_type = request.headers.get('content-type', '')
            if body and 'application/json' in content_type:
                log_data = json.loads(body.decode()) if body else {}
            else:
                log_data = {'raw_body': body.decode() if body else None}
        except (json.JSONDecodeError, UnicodeDecodeError):
            log_data = {'raw_body': '[binary_data]'}
        if auth_header and auth_header.startswith('Bearer'):
            logger.info(f"id: {id_user} - Запрос: {request.method} {request.url} {log_data}")  
        else:
            logger.info(f"Запрос: {request.method} {request.url} {log_data}")
    else: 
        if auth_header and auth_header.startswith('Bearer'):
            logger.info(f"id: {id_user} - Запрос: {request.method} {request.url}")  #
        else:
            logger.info(f"Запрос: {request.method} {request.url}")  
    try:               
        response = await call_next(request)
        response_body = b''.join([chunk async for chunk in response.body_iterator])
        str_body = response_body.decode()[:50]+"..." if response_body else '[empty]'
        logger.info(f"Ответ: {response.status_code} - {str_body}")
        return Response(
            content=response_body, 
            status_code=response.status_code, 
            media_type=response.media_type, 
            headers=response.headers
            )
    except Exception as exc:
        logger.error(f'500 Error: {str(exc)}')
    

@app.exception_handler(BaseAppException)
async def universal_exception_handler(request: Request, exc: BaseAppException):
    return JSONResponse(status_code=exc.status_code, content={'detail': exc.message})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
        content={'detail': 'Interal server error'},
        )


@app.get('/health')
async def welcome():
    return 'Welcom to Financial Manager!'


app.include_router(ws_router)
app.include_router(user_router)
app.include_router(category_router)
app.include_router(transaction_router)

