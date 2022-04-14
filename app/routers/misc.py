from fastapi import APIRouter, Depends, HTTPException, status as STATUS
from fastapi.security import OAuth2PasswordRequestForm
from app.auth import Token, UserAuth
from app.context import Context
from app.utils import get_tag_names

ctx = Context.instance()
tags = [
    {
        'name': 'misc',
        'description': 'Endpoints to authenticate and monitor the system.'
    }
]
router = APIRouter(tags=get_tag_names(tags))

@router.post('/token', response_model=Token,
             summary='Receive a bearer token as part of OAuth2')
async def authenticate(form_data: OAuth2PasswordRequestForm = Depends()):
    ua = UserAuth()
    if not ua.authenticate(form_data.username, form_data.password):
        raise HTTPException(
            status_code=STATUS.HTTP_401_UNAUTHORIZED,
            detail='Incorrect username or password',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    return ua.createToken()

@router.get('/ping', summary='Seng a ping to health-check the data store')
async def ping_redis():
    return (await ctx.redis.ping())
