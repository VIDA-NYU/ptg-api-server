from fastapi import APIRouter, Depends, HTTPException, Path, Query
from app.auth import UserAuth
from app.store import DataStore
from app.utils import get_tag_names, redis_id_to_iso

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
async def get_stream_ids():
    """
    Get the list of stream IDs available for sending and receiving
    data. These streams must have been created by the 'PUT' end-point
    and/or added directly by the data back-end (e.g. Redis) manually.
    """
    store = await DataStore.get()
    streamIds = await store.getStreamIds()
    return streamIds

@router.get('/{stream_id}', summary='Get information of a stream')
async def get_stream_info(
        sid: str = PARAM_STREAM_ID,
        report_error: bool | None = Query(False, desc="set to 'true' to return an error code if the stream is not found")):
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
    meta, info = await DataStore.getStreamInfo(sid)
    if hasattr(info, 'first-entry'):
        info['first-entry'] = redis_id_to_iso(info['first-entry'][0])
    if hasattr(info, 'last-entry'):
        info['last-entry'] = redis_id_to_iso(info['last-entry'][0])
    response = {'meta': meta, 'info': info}
    isError = type(meta)==str or type(info)==str
    if report_error and isError:
        raise HTTPException(status_code=400, detail=response)
    return response

@router.put('/{stream_id}', summary='Create or reset a stream')
async def create_stream(
        sid: str = PARAM_STREAM_ID,
        desc: str | None = Query(None, description='A short description of the stream'),
        meta: str | None = Query('{}', description='A JSON string to store stream-wide information'),
        override: bool | None = Query(False, desc="set to 'true' to replace the named stream with new parameters if exist"),
        max_len: int | None = None):
    """
    Create a new stream with the given ID and description. A stream
    must be created before data can be sent and received. Use
    *override* to silently update the stream parameters without
    returning an error. By default, `max_len` is set to the parameter
    in the `config.json` file, but can be overriden here.
    """
    store = await DataStore.get()
    if store.hasStreamId(sid) and not override:
        raise HTTPException(status_code=400,
                            detail=f"The stream '{sid}' already exists and 'override' is not specified.")
    await store.createStream(sid, desc=desc, meta=meta, max_len=max_len)
    return store.getStream(sid)

@router.delete('/{stream_id}', summary='Delete a stream')
async def delete_stream(
        sid: str = PARAM_STREAM_ID,
        force: bool | None = Query(False, desc="set to 'true' to not report error if the stream does not exist.")):
    """
    Delete the given stream ID. After this operation, the stream can no
    longer receive and send data through the API.
    """
    store = await DataStore.get()
    if not store.hasStreamId(sid) and not force:
        raise HTTPException(status_code=400,
                            detail=f"The requested stream '{sid}' does not exist.")
    return (await store.deleteStream(sid))
