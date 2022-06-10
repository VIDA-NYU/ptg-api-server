import asyncio
import datetime
from fastapi import APIRouter, Depends, Query, Path, HTTPException
from app.auth import UserAuth
from app.session import Session
from app.utils import get_tag_names

from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field
from fastapi import APIRouter, Depends, Body, Query, Path
from fastapi.encoders import jsonable_encoder
from app.auth import UserAuth
from app.session import Session
from app.utils import get_tag_names, AllOptional
from app.core.mongo import DB

session_db = DB('sessions')



tags = [
    {
        'name': 'session',
        'description': 'Manage recipe procedures and steps within a session'
    }
]
router = APIRouter(prefix='/sessions', tags=get_tag_names(tags),
                   dependencies=[Depends(UserAuth.require_authorization)])

PARAM_SESSION_ID = Path(None, alias='session_id', description='A session UID, e.g. linked to a set of camera streams')



class SessionSchema(BaseModel):
    device_id: Optional[int] = Field(0, description='The device this session is linked to.')
    recipe_id: Optional[str] = Field(description='The recipe id')
    step_index: Optional[int] = Field(0, description='The recipe step index')

    class Config:
        schema_extra = {
            # "example": {
            #     'id': 'grilled_cheese',
            #     'title': 'Grilled Cheese',
            # }
        }

class PartialSessionSchema(SessionSchema, metaclass=AllOptional):
    pass



@router.get("/", response_description="Get all sessions.")
async def get_all_sessions():
    return await session_db.get_all()

@router.get("/q", response_description="Search sessions.")
async def search_sessions(query: PartialSessionSchema = Depends()):
    return await session_db.get(**query.dict())

@router.get("/{session_id}", response_description="Get a specific session info by ID")
async def get_session(id: str = PARAM_SESSION_ID):
    return await session_db.get(id)

@router.post("/", response_description="Add a session")
async def new_session(data: SessionSchema = Body(...)):
    data.start_time = datetime.datetime.now().strftime('%c')
    return await session_db.add(jsonable_encoder(data))

@router.put("/{session_id}", response_description="Update a session")
async def update_session(id: str = PARAM_SESSION_ID, req: PartialSessionSchema = Body(...)):
    return await session_db.update(id, {k: v for k, v in req.dict().items() if v is not None})

@router.get("/{session_id}/step", response_description="Get the session step")
async def update_session_step(id: str = PARAM_SESSION_ID):
    return (await session_db.get(id))['step_index']

# NOTE: don't do relative steps +1 -1 for obvs lack of locking reasons
@router.put("/{session_id}/step/{step}", response_description="Update the session step")
async def update_session_step(id: str = PARAM_SESSION_ID, step: int = Query(description="The current step index to update to")):
    return await session_db.update(id, {'step_index': step})

@router.delete("/{session_id}", response_description="Delete a session")
async def delete_session(id: str = PARAM_SESSION_ID):
    return await session_db.delete(id)
