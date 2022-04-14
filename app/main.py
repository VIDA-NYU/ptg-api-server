from fastapi import FastAPI, APIRouter, Response
from app.context import Context
from app.routers import data, misc, streams

ctx = Context.instance()
routers = [misc, streams, data, ]
tags = sum(map(lambda x: x.tags, routers), [])
app = FastAPI(title=ctx.config['title'],
              description=ctx.getDescription(),
              openapi_tags=tags,
              root_path=ctx.config['root_path'])
for r in routers:
    app.include_router(r.router)
app.mount(ctx.config['root_path'], app)

@app.on_event('startup')
async def startup():
    await ctx.initialize()
