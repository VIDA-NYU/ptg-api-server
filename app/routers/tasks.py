# import io
# import orjson
# from celery.result import AsyncResult
# from fastapi import APIRouter, Depends, Query, Path, HTTPException, File, Request, WebSocket, WebSocketDisconnect
# from fastapi.responses import StreamingResponse
# from websockets.exceptions import ConnectionClosed
# from app.auth import UserAuth
# from app.store import DataStream
# from app.utils import get_tag_names, pack_entries

# tags = [
#     {
#         'name': 'tasks',
#         'description': 'Start and stop background tasks'
#     }
# ]
# router = APIRouter(prefix='/tasks', tags=get_tag_names(tags),
#                    dependencies=[Depends(UserAuth.require_authorization)])

# PARAM_STREAM_ID = Path(None, alias='stream_id', description='The unique ID of the stream')
# PARAM_TASK_ID = Path(None, alias='task_id', description='The task ID returned when starting the stream.')

# @router.post('/{stream_id}/start', summary='Start recording data')
# async def record_streams_start(stream_id: str=PARAM_STREAM_ID):
#     return 

# @router.post('/{task_id}/status', summary='Check recording status')
# async def record_streams_status(task_id: str=PARAM_TASK_ID):
#     res = AsyncResult("your-task-id")
#     res.ready()
#     return 

# @router.post('/{task_id}/stop', summary='Stop recording data')
# async def record_streams_stop(task_id: str=PARAM_TASK_ID):
#     return 
