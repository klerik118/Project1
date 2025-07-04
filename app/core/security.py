from typing import Optional

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, status, Header
import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import auth, BaseAppException
from app.core.database import get_async_session
from app.repositories.user import UserRepository


http_bearer = HTTPBearer(scheme_name='JWT Token', description='Token')


async def decod_token(credential: HTTPAuthorizationCredentials = Depends(http_bearer)) -> Optional[int]:
    try:
        token = credential.credentials
        decod = jwt.decode(token, auth.public_key_path.read_text(), auth.algorithm)
        type_token = decod.get('type') 
        id: str = decod.get('sub')
        if not id:
            raise BaseAppException(status_code=status.HTTP_401_UNAUTHORIZED, massege='Incorrect data')
        if type_token != 'access':
            raise BaseAppException(status_code=status.HTTP_401_UNAUTHORIZED, message='Not access token') 
        return int(id)
    except jwt.ExpiredSignatureError:
        raise BaseAppException(status_code=status.HTTP_401_UNAUTHORIZED, message='Expired token') 
    except (jwt.InvalidTokenError, jwt.DecodeError, jwt.InvalidSignatureError):
        raise BaseAppException(status_code=status.HTTP_401_UNAUTHORIZED, message='Error token!')
    

async def get_id_current_user(
        id: int = Depends(decod_token), 
        session: AsyncSession = Depends(get_async_session)
        ) -> Optional[int]:
    user_id = await UserRepository.checking_user_id(session, id)
    if not user_id:
        raise BaseAppException(status_code=status.HTTP_404_NOT_FOUND, message='This user does not exist')
    return user_id


async def token_verification(
        access_token: HTTPAuthorizationCredentials = Depends(http_bearer),
        refresh_token: str = Header(..., alias='Refresh-Token')
        ) -> Optional[str]:
    try:
        token = access_token.credentials
        decod = jwt.decode(token, auth.public_key_path.read_text(), auth.algorithm, options={'verify_exp': False})
        access_id: str = decod.get('sub')
        access_type = decod.get('type')
        decod = jwt.decode(refresh_token, auth.public_key_path.read_text(), auth.algorithm)
        refresh_id: str = decod.get('sub')
        refresh_type = decod.get('type')
    except jwt.PyJWTError:
        raise BaseAppException(status_code=status.HTTP_401_UNAUTHORIZED, message='Error token!')
    if access_type == 'access' and refresh_type == 'refresh' and access_id == refresh_id:
        return access_id
    else:
        raise BaseAppException(status_code=status.HTTP_401_UNAUTHORIZED, message='Error token!')
    

    
