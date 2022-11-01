import os
import glob

import mimetypes

import orjson
from fastapi import APIRouter, Depends, Query, Path, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from app.auth import UserAuth
from app.core.recordings import Recordings, RecordingPlayer
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
PARAM_NEW_RECORDING_ID = Path(description='The new ID of the recording.')

@router.get('/', summary='List recordings')
async def list_recordings(info: bool | None = PARAM_INFO, cache: bool=True):
    if info:
        return await RECORDINGS.list_recording_info(cache=cache)
    return RECORDINGS.list_recordings()


@router.delete('/cache', summary='cache recording info cache')
async def clear_recording_info_cache():
    return await RECORDINGS.clear_recording_info_cache()

@router.get('/current', summary='Get current recording info')
async def get_current_recording_info(info: bool | None = PARAM_INFO):
    return await RECORDINGS.get_current_recording(info=info)


@router.get('/{recording_id}', summary='Get recording info')
async def get_recording_info(recording_id: str = PARAM_RECORDING_ID):
    return await RECORDINGS.get_recording_info(recording_id)



@router.put('/start', summary='Start recording data')
async def record_streams_start(rec_id: str | None = Query(None, description="specify a recording ID (optional)")):
    return await RECORDINGS.start(rec_id)

@router.put('/stop', summary='Stop recording data')
async def record_streams_stop():
    return await RECORDINGS.stop()

@router.put('/{recording_id}/rename/{new_id}', summary='rename recording')
async def rename_recording(recording_id: str = PARAM_RECORDING_ID, new_id: str=PARAM_NEW_RECORDING_ID):
    return RECORDINGS.rename_recording(recording_id, new_id)

@router.delete('/{recording_id}', summary='delete recording')
async def delete_recording(recording_id: str = PARAM_RECORDING_ID):
    return RECORDINGS.delete_recording(recording_id)

@router.put('/{recording_id}/hide', summary='hide recording')
async def hide_recording(recording_id: str = PARAM_RECORDING_ID):
    return RECORDINGS.hide_recording(recording_id)

@router.put('/{recording_id}/unhide', summary='unhide recording')
async def unhide_recording(recording_id: str = PARAM_RECORDING_ID):
    return RECORDINGS.unhide_recording(recording_id)


@router.websocket('/replay')
async def replay_recording(
        ws: WebSocket,
        rec_id: str = Query(None, description="the recording ID"),
        prefix: str | None = Query("", description="the output prefix"),
        sid: str | None = Query("main", description="the stream id(s) to be replayed, can be joined by '+'"),
        fullspeed: bool | None = Query(False, description="set to true to replay as fast as possible"),
        interval: float | None = Query(1.0, description="the time delay between progress updates"),
    ):
    """
    """
    if not (await UserAuth.authorizeWebSocket(ws)):
        return
    await ws.accept()
    player = RecordingPlayer()
    await player.replay(ws, rec_id, prefix, sid.split('+'), fullspeed, interval)
