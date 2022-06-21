from __future__ import annotations
import asyncio
# import datetime
from fastapi import APIRouter, Depends, Query, Path, HTTPException
from app.auth import UserAuth
# from app.session import Session
from app.utils import get_tag_names

from typing import List, Optional
# from pydantic import BaseModel, EmailStr, Field
from fastapi import APIRouter, Depends, Body, Query, Path
# from fastapi.encoders import jsonable_encoder
from app.auth import UserAuth
# from app.session import Session
from app.utils import get_tag_names, AllOptional
from app.context import Context
# from app.core.mongo import DB
from app.routers import recipes  # TODO: import db from 3rd place? instead of from router

ctx = Context.instance()

# session_db = DB('sessions')


RECIPE_ID = 'recipe:id'
RECIPE_STEP = 'recipe:step'
class Session:
    def __init__(self) -> None:
        pass

    async def get_session(self):
        id, step = await session.get_keys(RECIPE_ID, RECIPE_STEP)
        return dict(recipe_id=id, step=step)

    async def current_recipe(self, info=False):
        id = await ctx.redis.get(RECIPE_ID)
        if info:
            return await recipes.recipe_db.get(id)
        return id

    async def start_recipe(self, id: str):
        async with ctx.redis.pipeline() as pipe:
            pipe.set(RECIPE_ID, id)
            pipe.set(RECIPE_STEP, 0)
            return await pipe.execute()

    async def clear_recipe(self):
        async with ctx.redis.pipeline() as pipe:
            pipe.delete(RECIPE_ID)
            pipe.delete(RECIPE_STEP)
            return await pipe.execute()

    async def get_recipe_step(self):
        step_index: int = await ctx.redis.get(RECIPE_STEP) or 0
        return step_index

    async def set_recipe_step(self, step_index: int):
        return await ctx.redis.get(RECIPE_STEP, step_index)

    async def get_keys(self, *keys: str, asdict=True):
        with  ctx.redis.pipeline() as pipe:
            for k in keys:
                pipe.get(k)
            values = await pipe.execute()
            return dict(zip(keys, values)) if asdict else values



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

@router.put('/recipe/{recipe_id}', summary='Start recipe')
async def start_recipe(recipe_id: str = Query(None, description="set the current recipe")):
    return await session.start_recipe(recipe_id)

@router.put('/recipe', summary='Stop recipe')
async def stop_recipe():
    return await session.clear_recipe()

@router.get("/recipe/step", response_description="Get the current recipe step")
async def get_session_recipe_step():
    return await session.get_recipe_step()

# @router.put('/recipe/step', summary='Reset recipe step')
@router.put('/recipe/step/{step_id}', summary='Set recipe step')
async def set_session_recipe_step(step_id: int = Query(0, description="set the current recipe step")):
    return await session.set_recipe_step(step_id)
