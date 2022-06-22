from app.context import Context
from app.routers import recipes  # TODO: import db from 3rd place? instead of from router

ctx = Context.instance()



RECIPE_ID = 'recipe:id'
RECIPE_STEP = 'recipe:step'
class Session:
    def __init__(self) -> None:
        pass

    async def get_session(self):
        id, step = await self.get_keys(RECIPE_ID, RECIPE_STEP)
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

