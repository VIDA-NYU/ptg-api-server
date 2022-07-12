import os
import glob

import mimetypes

import orjson
from fastapi import APIRouter, Depends, Query, Path, Header, HTTPException, File, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from app.auth import UserAuth
from app.core.recordings import Recordings, RECORDING_POST_PATH
from app.utils import get_tag_names

RECORDINGS = Recordings()


tags = [
    {
        'name': 'recordings',
        'description': 'Start and stop data recording'
    }
]
router = APIRouter(prefix='/recordings', tags=get_tag_names(tags),
                   dependencies=[Depends(UserAuth.require_authorization)])


PARAM_RECORDING_ID = Path(description='The ID of the recording.')
PARAM_INFO  = Query(False, description="set to 'true' to return recording metadata as well")

@router.get('/', summary='List recordings')
async def list_recordings(info: bool | None = PARAM_INFO):
    if info:
        return RECORDINGS.list_recording_info()
    return RECORDINGS.list_recordings()


@router.get('/current', summary='Get current recording info')
async def get_current_recording_info(info: bool | None = PARAM_INFO):
    return await RECORDINGS.get_current_recording(info=info)


@router.get('/{recording_id}', summary='Get recording info')
async def get_recording_info(recording_id: str = PARAM_RECORDING_ID):
    return RECORDINGS.get_recording_info(recording_id)



@router.put('/start', summary='Start recording data')
async def record_streams_start(rec_id: str | None = Query(None, description="specify a recording ID (optional)")):
    return await RECORDINGS.start(rec_id)

@router.put('/stop', summary='Stop recording data')
async def record_streams_stop():
    return await RECORDINGS.stop()


