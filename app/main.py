import patch  # fastapi fixes
from fastapi import FastAPI, APIRouter, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette_exporter import PrometheusMiddleware, handle_metrics
from app.context import Context
from app.routers import data, misc, streams, recipes, session, recording

ctx = Context.instance()
routers = [misc, streams, data, recipes, session, recording]
tags = sum(map(lambda x: x.tags, routers), [])

app = FastAPI(title=ctx.config['title'],
              description=ctx.getDescription(),
              openapi_tags=tags,
              root_path=ctx.config['root_path'])

for r in routers:
    app.include_router(r.router)

# app.mount(ctx.config['root_path'], app)  # causing recursive error
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

app.add_middleware(PrometheusMiddleware)
app.add_route("/metrics", handle_metrics)


@app.on_event('startup')
async def startup():
    await ctx.initialize()


@app.exception_handler(Exception)
async def validation_exception_handler(request, err):
    return JSONResponse(status_code=500, content={
        # "error": True,
        # "message": f"({type(err).__name__}) {err}",
        'detail': [
            {'msg': str(err), 'type': type(err).__name__}
        ]
    })
