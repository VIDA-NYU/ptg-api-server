import asyncio
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Body
from app.auth import UserAuth
# from app.store import DataStore
from app.core.streams import Streams
from app.utils import get_tag_names, redis_id_to_iso


STREAM_STORE = Streams()

tags = [
    {
        'name': 'streams',
        'description': 'Managing data streams (not the actual data), e.g. creating a stream, setting stream parameters, etc.'
    }
]
router = APIRouter(prefix='/streams',
                   tags=get_tag_names(tags),
                   dependencies=[Depends(UserAuth.require_authorization)])

PARAM_STREAM_ID = Path(None, alias='stream_id', description='The unique ID of the stream')

@router.get('/', summary="Get available streams")
async def get_stream_ids(info: bool | None = Query(False, description="set to 'true' to return stream metadata as well")):
    """
    Get the list of stream IDs available for sending and receiving
    data. These streams must have been created by the 'PUT' end-point
    and/or added directly by the data back-end (e.g. Redis) manually.
    """
    if info:
        return await STREAM_STORE.list_stream_info()
    return await STREAM_STORE.list_streams()
    

@router.get('/{stream_id}', summary='Get information of a stream')
async def get_stream_info(
        sid: str = PARAM_STREAM_ID,
        report_error: bool | None = Query(False, description="set to 'true' to return an error code if the stream is not found")):
    """
    Return two pieces information of the provided stream ID:
    
    - **meta**: the parameters configured when creating the stream,
        e.g. `id`, `max_len`, etc.
    - **info**: the stream statistics on the back-end (e.g. equivalent
        to what returned by Redis's `XINFO STREAM`)

    Note that by default, if there's an error in retrieving the above
    information, the call still succeeds (with a 200 status code)
    and the error message(s) will be returned in the response. If an
    error status code (400) is desired, set **report_error** to true.
    """
    info = await STREAM_STORE.get_stream_info(sid)
    if report_error and 'error' in info:
        raise HTTPException(status_code=400, detail=info['error'])
    return info

@router.put('/{stream_id}', summary='Update a streams metadata')
async def update_stream(
        sid: str = PARAM_STREAM_ID,
        # desc: str | None = Query(None, description='A short description of the stream'),
        meta: dict = Body(..., description='arbitrary metadata to store with the stream'),
        override: bool | None = Query(False, description="set to 'true' to replace the named stream with new parameters if exist")):
    """
    Create a new stream with the given ID and description. A stream
    must be created before data can be sent and received. Use
    *override* to silently update the stream parameters without
    returning an error. By default, `max_len` is set to the parameter
    in the `config.json` file, but can be overriden here.
    """
    await STREAM_STORE.set_stream_meta(sid, _update=not override, **meta)
    return await STREAM_STORE.get_stream_meta(sid)

@router.delete('/{stream_id}', summary='Delete a stream')
async def delete_stream(sid: str = PARAM_STREAM_ID):
    """Delete the given stream ID. After this operation, the stream can no
    longer receive and send data through the API.
    """
    return await STREAM_STORE.delete_stream(sid)
