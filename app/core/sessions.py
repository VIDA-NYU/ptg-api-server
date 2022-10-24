import time
from app.context import Context
from app.routers import recipes  # TODO: import db from 3rd place? instead of from router
from app.core.streams import Streams
from app.core.mongo import DB

db = DB('sessions')

ctx = Context.instance()

STREAM_STORE = Streams()

RECIPE_ID = 'recipe:id'
RECIPE_STEP = 'recipe:step'
SESSION_ID = 'session:id'
class Sessions:
    def __init__(self) -> None:
        pass

    async def ls(self):
        return await db.get_all()

    async def get(self, sess_id):
        return await db.get(sess_id)

    async def search(self, **query):
        return await db.get(**query)

    async def new(self, **data):
        return await db.add(**data)

    async def update(self, sess_id, **data):
        return await db.update(sess_id, {
            k: v for k, v in data.items()
            if v is not None
        })

    async def delete(self, sess_id):
        return await db.delete(sess_id)







    async def get_session(self):
        id, step = await self.get_keys(RECIPE_ID, RECIPE_STEP, SESSION_ID, asdict=False)
        return dict(recipe_id=id, step=step)

    async def current_recipe(self, info=False):
        id = await ctx.redis.get(RECIPE_ID)
        if info:
            return await recipes.recipe_db.get(id)
        return id

    async def current_session_id(self):
        id = await ctx.redis.get(SESSION_ID)
        return id

    async def start_recipe(self, id: str):
        recipe = await recipes.recipe_db.get(id)
        if not recipe:
            raise ValueError(f"Recipe {id} not found.")
        session_id = str(int(time.time()))
        async with ctx.redis.pipeline() as pipe:
            pipe.set(RECIPE_ID, id)
            pipe.set(RECIPE_STEP, 0)
            pipe.set(SESSION_ID, session_id)
            pipe.xadd(f'event:{RECIPE_ID}', {b'd': id}, '*', maxlen=10, approximate=True)
            pipe.xadd(f'event:{RECIPE_STEP}', {b'd': 0}, '*', maxlen=100, approximate=True)
            pipe.xadd(f'event:{SESSION_ID}', {b'd': session_id}, '*', maxlen=100, approximate=True)
            return await pipe.execute()

    async def clear_recipe(self):
        async with ctx.redis.pipeline() as pipe:
            pipe.delete(RECIPE_ID)
            pipe.delete(RECIPE_STEP)
            pipe.delete(SESSION_ID)
            pipe.xadd(f'event:{RECIPE_ID}', {b'd': ''}, '*', maxlen=10, approximate=True)
            pipe.xadd(f'event:{RECIPE_STEP}', {b'd': -1}, '*', maxlen=100, approximate=True)
            pipe.xadd(f'event:{SESSION_ID}', {b'd': ''}, '*', maxlen=10, approximate=True)
            return await pipe.execute()

    async def get_recipe_step(self):
        step_index = await ctx.redis.get(RECIPE_STEP)
        return step_index

    async def set_recipe_step(self, step_index: int):
        async with ctx.redis.pipeline() as pipe:
            pipe.set(RECIPE_STEP, step_index)
            pipe.xadd(f'event:{RECIPE_STEP}', {b'd': step_index}, '*', maxlen=100, approximate=True)
            pipe.get(RECIPE_STEP)
            return await pipe.execute()

    async def get_keys(self, *keys: str, asdict=True):
        async with ctx.redis.pipeline() as pipe:
            for k in keys:
                pipe.get(k)
            values = await pipe.execute()
            return dict(zip(keys, values)) if asdict else values

