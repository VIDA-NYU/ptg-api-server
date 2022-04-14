import io
import orjson
from fastapi import APIRouter, Depends, Query, Path, HTTPException, File, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from websockets.exceptions import ConnectionClosed
from app.auth import UserAuth
from app.store import DataStream
from app.utils import get_tag_names, pack_entries

tags = [
    {
        'name': 'data',
        'description': 'Send and receive data through the streams created with the "streams" endpoints'
    }
]
router = APIRouter(prefix='/data', tags=get_tag_names(tags),
                   dependencies=[Depends(UserAuth.require_authorization)])

PARAM_STREAM_ID = Path(None, alias='stream_id', description='The unique ID of the stream')

@router.post('/{stream_id}', summary='Send data to a stream')
async def send_data_entries(
        sid: str = PARAM_STREAM_ID,
        entries: list[bytes] | None = File(..., desc='A list of data entries (as multiform files) to be added into the stream.')):
    res = await DataStream.addEntries(sid, entries)
    return res

@router.get('/{stream_id}', summary='Retrieve data from a stream', response_class=StreamingResponse)
async def get_data_entries(
        sid: str = PARAM_STREAM_ID,
        count:  int | None = Query(1, desc="The maximum number of elements to be returned"),
        last_entry_id: str | None = Query('*', desc="Only retrieve entries later than the provided ID")):
    """This retrieves **count** elements that have later timestamps
    than **last_entry_id** from the specified data stream. The entry
    ID should be in the form of:

    `<millisecondsTime>-<sequenceNumber>` 

    More info can be found on [Redis's
    documentation](https://redis.io/docs/manual/data-types/streams/#entry-ids). Special
    IDs such as `0` and `$` are also accepted. In addition, if
    **last_entry_id** is a `*`, the latest **count** entries
    will be returned.

    If successful, the response header will include an `entry-offset`
    field describing the offsets of the batch
    `[[entry_id,offset],...]` in the return data.

    """
    try:
        entries = await DataStream.getEntries(sid, count, last_entry_id)
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err))
    offsets, content = pack_entries(entries)
    return StreamingResponse(io.BytesIO(content),
                             headers={'entry-offset': offsets},
                             media_type='application/octet-stream')

@router.websocket(router.prefix + '/{stream_id}/push')
async def push_data_ws(
        ws: WebSocket,
        sid: str = PARAM_STREAM_ID,
        batch:  bool | None = Query(False, desc="set to 'true' if entries will be sent in batches (alternate one text, one bytes)"),
        ack: bool | None = Query(False, desc="set to 'true' if would like the server to respond to each entry/batch with inserted entry IDs")):
    """
    """
    if not (await UserAuth.authorizeWebSocket(ws)):
        return
    await ws.accept()
    try:
        while True:
            if batch:
                offsets = list(map(int, (await ws.receive_text()).split(',')))
            data = await ws.receive_bytes()
            if batch:
                offsets.append(len(data))
                entries = map(lambda x: data[offsets[x]:offsets[x+1]], range(len(offsets)-1))
            else:
                entries = [data]
            res = await DataStream.addEntries(sid, entries)
            if ack:
                ids = ','.join(map(lambda x: x.decode('utf-8'), res))
                await ws.send_text(ids)
    except (WebSocketDisconnect, ConnectionClosed):
        pass


@router.websocket(router.prefix + '/{stream_id}/pull')
async def pull_data_ws(
        ws: WebSocket,
        sid: str = PARAM_STREAM_ID,
        count:  int | None = Query(1, desc="the maximum number of entries for each receive"),
        last_entry_id: str | None = Query('$', desc="Start retrieving entries laters than the provided ID")):
    """
    """
    if not (await UserAuth.authorizeWebSocket(ws)):
        return
    await ws.accept()
    try:
        last = last_entry_id
        while True:
            entries = await DataStream.getEntries(sid, count, last, block=10000)
            if entries:
                offsets, content = pack_entries(entries)
                await ws.send_text(offsets)
                await ws.send_bytes(content)
                last = entries[-1][0]
    except (WebSocketDisconnect, ConnectionClosed):
        pass
        
