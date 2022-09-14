from __future__ import annotations
from fastapi import APIRouter, Depends, Query, Path, HTTPException

from app.auth import UserAuth
from app.core.session import Session
from app.utils import get_tag_names
from app.context import Context

ctx = Context.instance()


session = Session()


tags = [
    {
        'name': 'session',
        'description': 'Manage recipe procedures and steps within a session'
    }
]
router = APIRouter(prefix='/sessions', tags=get_tag_names(tags),
                   dependencies=[Depends(UserAuth.require_authorization)])

PARAM_SESSION_ID = Path(None, alias='session_id', description='A session UID, e.g. linked to a set of camera streams')

@router.get("/", response_description="Get all sessions.")
async def get_all_sessions():
    return await session.get_session()

@router.get("/recipe", response_description="Get a specific session info by ID")
async def get_recipe(info: bool | None = Query(False, description="set to 'true' to return recipe metadata as well")):
    return await session.current_recipe(info=info or False)

@router.get('/id', summary='Get current session id')
async def get_session_id():
    return await session.current_session_id()

@router.put('/recipe/{recipe_id}', summary='Start recipe')
async def start_recipe(recipe_id: str = Query(None, description="set the current recipe")):
    return await session.start_recipe(recipe_id)

@router.delete('/recipe', summary='Stop recipe')
async def stop_recipe():
    return await session.clear_recipe()

@router.get("/recipe/step", response_description="Get the current recipe step")
async def get_session_recipe_step():
    return await session.get_recipe_step()

# @router.put('/recipe/step', summary='Reset recipe step')
@router.put('/recipe/step/{step_id}', summary='Set recipe step')
async def set_session_recipe_step(step_id: int = Query(0, description="set the current recipe step")):
    return await session.set_recipe_step(step_id)
