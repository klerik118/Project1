import os

from pydantic import BaseModel
from dotenv import load_dotenv
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler


BASE_DIR = Path(__file__).parent.parent.parent

load_dotenv()

DB_HOST = os.environ.get('DB_HOST')

DB_PORT = os.environ.get('DB_PORT')

DB_NAME = os.environ.get('DB_NAME')

DB_USER = os.environ.get('DB_USER')

DB_PASSWORD = os.environ.get('DB_PASSWORD')

SECRET_KEY_JWT = os.environ.get('SECRET_KEY_JWT')


class AuthJWT(BaseModel):
    private_key_path: Path = BASE_DIR / ".secret_key" / "private_key.pem"
    public_key_path: Path = BASE_DIR / ".secret_key" / "public_key.pem"
    algorithm: str = "RS256"
    expiration: int = 60
    refresh_exp : int = 1


auth = AuthJWT()


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(module)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), RotatingFileHandler('logs/app_log', maxBytes=5*1024, backupCount=2)] 
    )

logger = logging.getLogger()


class BaseAppException(Exception):
    def __init__(self, message: str = '', status_code: int = 500):
        self.message = message
        self.status_code = status_code


redis_expire = 86400