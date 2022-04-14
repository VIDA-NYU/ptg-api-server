import datetime
from fastapi import Depends, FastAPI, HTTPException, status as STATUS
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel
from app.context import Context

ctx = Context.instance()


SECRET_KEY = '56b0bde8ca81e3b8f1b2b9c0f76d73a8a1ee7083b003f5e5811d35f5f266d4b5' # openssl rand -hex 32
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 60*24*30 # 30-day valid token, never expire for now
oauth2 = OAuth2PasswordBearer(tokenUrl='token')

class Token(BaseModel):
    access_token: str
    token_type: str

class User(BaseModel):
    username: str

class UserAuth:

    def __init__(self, username: str | None = None, password: str | None = None):
        self.user = None

    def authenticate(self, username: str, password: str):
        # TODO: check if username is in db, and pass is valid
        # For now, authenticate any users
        if username=='' or username!=password:
            return False
        self.user = User(username=username)
        return True

    def createToken(self):
        exp = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        token = {
            'sub': self.user.username,
            'exp': exp,
        }
        token = jwt.encode(token, SECRET_KEY, algorithm=ALGORITHM)
        return {'access_token': token, 'token_type': 'bearer'}

    @staticmethod
    async def authorizeWebSocket(ws):
        try:
            token = await oauth2(ws)
            return await UserAuth.require_authorization(token)
        except:
            pass

    @staticmethod
    async def require_authorization(token: str = Depends(oauth2)):
        tokenError = HTTPException(
            status_code=STATUS.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                raise tokenError
        except JWTError:
            raise tokenError
        return User(username=username)
        
