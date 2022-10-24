import re
import time
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field
from fastapi import APIRouter, Depends, Body, Path
from fastapi.encoders import jsonable_encoder
from app.auth import UserAuth
# from app.session import Session
from app.utils import get_tag_names, AllOptional
from app.core.mongo import DB

db = DB('sessions')

tags = [
    {
        'name': 'sessions2',
        'description': 'Manage multiple sessions'
    }
]

router = APIRouter(prefix='/sess', tags=get_tag_names(tags),
                   dependencies=[Depends(UserAuth.require_authorization)])


class SessionSchema(BaseModel):
    id: str = Field(None, description='The session id')
    recipe: str = Field(None, description='The session recipe')
    step: int = Field(0, description='The session step')
    prefix: str = Field(None, description='The session stream prefix')

class PartialSessionSchema(SessionSchema, metaclass=AllOptional):
    pass


PARAM_SESSION_ID = Path(None, description='The session UID')


@router.get("/", response_description="Get all sessions")
async def get_all():
    return await db.get_all()

@router.get("/q", response_description="Search sessions.")
async def search_sessions(query: PartialSessionSchema = Depends()):
    return await db.get(**query.dict())

@router.get("/{id}", response_description="Get a specific session")
async def get_data(id: str = PARAM_SESSION_ID):
    return await db.get(id)

@router.post("/", response_description="Add a session")
async def add_session(data: SessionSchema = Body(...)):
    if not data.id:
        data.id = b36intencode(int(time.time()))
    d=data.dict()
    d['created_at'] = datetime.now().isoformat()
    return await db.add(d)

@router.put("/{id}", response_description="Update a session")
async def update_data(id: str = PARAM_SESSION_ID, data: PartialSessionSchema = Body(...)):
    return await db.update(id, {
        k: v for k, v in data.dict().items() 
        if v is not None
    })

@router.delete("/{id}", response_description="Delete a session")
async def delete_data(id: str = PARAM_SESSION_ID):
    return await db.delete(id)


ALPHABET = '0123456789abcdefghijklmnopqrstuvwxyz'
def b36intencode(number, base=None, zeros=None):
    """Converts an integer to a base36 string."""
    base = base or len(ALPHABET)
    sign = '-' if number < 0 else ''
    number = abs(int(number))
    enc = ''
    while number:
        number, i = divmod(number, base)
        enc = ALPHABET[i] + enc
    return sign + ('{:0>{}}'.format(enc, zeros) if zeros else enc)
