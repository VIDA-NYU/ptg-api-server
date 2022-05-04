# add up one directory to path
import os
import sys
sys.path.insert(0, os.path.abspath(f'{__file__}/../..'))
print(sys.path)

from fastapi import FastAPI, APIRouter, Response
from fastapi.middleware.cors import CORSMiddleware
from app.context import Context
from app.routers import data, misc, procedure, streams

ctx = Context.instance()
routers = [misc, streams, data, procedure]
tags = sum(map(lambda x: x.tags, routers), [])
app = FastAPI(title=ctx.config['title'],
              description=ctx.getDescription(),
              openapi_tags=tags,
              root_path=ctx.config['root_path'])
for r in routers:
    app.include_router(r.router)
app.mount(ctx.config['root_path'], app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

@app.on_event('startup')
async def startup():
    await ctx.initialize()
