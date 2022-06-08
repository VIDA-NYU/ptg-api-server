import io
import orjson
from fastapi import APIRouter, Depends, Query, Path, HTTPException, File, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from websockets.exceptions import ConnectionClosed
from app.auth import UserAuth
# from app.store import DataStream
from app.utils import get_tag_names, pack_entries


tags = [
    {
        'name': 'recordings',
        'description': 'Start and stop data recording'
    }
]
router = APIRouter(prefix='/recordings', tags=get_tag_names(tags),
                   dependencies=[Depends(UserAuth.require_authorization)])


PARAM_RECORDING_ID = Path(description='The ID of the recording.')

@router.post('/', summary='List recordings')
async def list_recordings():
    return 

@router.post('/{recording_id}', summary='Get recording info')
async def get_recording_info(recording_id: str = PARAM_RECORDING_ID):
    return 



@router.post('/start', summary='Start recording data')
async def record_streams_start():
    return 

@router.post('/stop', summary='Stop recording data')
async def record_streams_stop():
    return 
