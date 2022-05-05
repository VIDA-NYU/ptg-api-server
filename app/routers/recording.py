# import io
# import orjson
# from fastapi import APIRouter, Depends, Query, Path, HTTPException, File, Request, WebSocket, WebSocketDisconnect
# from fastapi.responses import StreamingResponse
# from websockets.exceptions import ConnectionClosed
# from app.auth import UserAuth
# from app.store import DataStream
# from app.utils import get_tag_names, pack_entries

# STREAM_ID_SEP = ':'

# tags = [
#     {
#         'name': 'recording',
#         'description': 'Start and stop data recording'
#     }
# ]
# router = APIRouter(prefix='/recording', tags=get_tag_names(tags),
#                    dependencies=[Depends(UserAuth.require_authorization)])

# PARAM_STREAM_ID = Path(None, alias='stream_id', description='The unique ID of the stream')
# PARAM_TASK_ID = Path(None, alias='task_id', description='The task ID returned when starting the stream.')

# @router.post('/status', summary='Check all recording status')
# async def record_streams_status(task_id: str=PARAM_TASK_ID):
#     return 

# @router.post('/{stream_id}/start', summary='Start recording data')
# async def record_streams_start(stream_id: str=PARAM_STREAM_ID):
#     return 

# @router.post('/{task_id}/status', summary='Check recording status')
# async def record_streams_status(task_id: str=PARAM_TASK_ID):
#     return 

# @router.post('/{task_id}/stop', summary='Stop recording data')
# async def record_streams_stop(task_id: str=PARAM_TASK_ID):
#     return 


# def stream_id_prefix_match(a, b):
#     a = a.split(STREAM_ID_SEP)
#     b = b.split(STREAM_ID_SEP)
#     l = min(len(a), len(b))
#     return a[:l] == b[:l]