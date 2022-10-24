import os
import patch  # fastapi fixes
import aiofiles
from fastapi import FastAPI, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette_exporter import PrometheusMiddleware, handle_metrics
from app.context import Context
from app.core.recordings import RECORDING_POST_PATH, RECORDING_RAW_PATH
from app.static import AuthStaticFiles
from app.routers import data, misc, streams, recipes, session, sessions, recording, mjpeg

ctx = Context.instance()
routers = [misc, streams, data, recipes, session, sessions, recording, mjpeg]
tags = [t for r in routers for t in r.tags]

app = FastAPI(title=ctx.config['title'],
              description=ctx.getDescription(),
              openapi_tags=tags,
              root_path=ctx.config['root_path'])

for r in routers:
    app.include_router(r.router)

app.mount(
    "/recordings/static", 
    AuthStaticFiles(directory=RECORDING_POST_PATH), 
    name="recording files")

# XXX: not sure with order of precidence
app.mount(
    "/recordings/static/raw",
    AuthStaticFiles(directory=RECORDING_RAW_PATH),
    name="raw recording files")

@app.post("/recordings/upload/{recording_id}/{fname}")
async def create_upload_file(recording_id: str, fname: str, file: UploadFile, overwrite: bool=False):
    assert recording_id and fname, "must specify recording ID and filename"
    fname = os.path.normpath(os.path.join(*recording_id.split('/'), *fname.split('/')))
    full_path = os.path.join(RECORDING_POST_PATH, fname)
    if not overwrite and os.path.isfile(full_path):
        raise OSError(f"File {fname} already exists.")
    async with aiofiles.open(full_path, 'wb') as out_file:
        while content := await file.read(1024):
            await out_file.write(content)
    return {"filename": fname, "url": f"/recordings/static/{fname}"}


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

# app.mount(ctx.config['root_path'], app)  # causing recursive error
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=['*'],
    #allow_methods=['*'],
    allow_headers=['*'],
    allow_methods=["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"],
)
