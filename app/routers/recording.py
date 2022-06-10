import os
import glob

import orjson
from fastapi import APIRouter, Depends, Query, Path, HTTPException, File, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from app.auth import UserAuth
from app.recordings import Recordings
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

@router.get('/', summary='List recordings')
async def list_recordings(info: bool | None = Query(False, description="set to 'true' to return recording metadata as well")):
    if info:
        return RECORDINGS.list_recording_info()
    return RECORDINGS.list_recordings()

@router.get('/{recording_id}', summary='Get recording info')
async def get_recording_info(recording_id: str = PARAM_RECORDING_ID):
    return RECORDINGS.get_recording_info(recording_id)



@router.put('/start', summary='Start recording data')
async def record_streams_start(rec_id: str | None = Query(None, description="specify a recording ID (optional)")):
    return await RECORDINGS.start(rec_id)

@router.put('/stop', summary='Stop recording data')
async def record_streams_stop():
    return await RECORDINGS.stop()
