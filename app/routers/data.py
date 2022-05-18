import asyncio
import io
import itertools
import orjson
import re
from fastapi import APIRouter, Depends, Query, Path, HTTPException, File, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from websockets.exceptions import ConnectionClosed
from app.auth import UserAuth
from app.store import DataStream
from app.utils import get_tag_names, unzip_entries, prints_traceback
from app import holoframe

tags = [
    {
        'name': 'data',
        'description': 'Send and receive data through the streams created with the "streams" endpoints'
    }
]
router = APIRouter(prefix='/data', tags=get_tag_names(tags),
                   dependencies=[Depends(UserAuth.require_authorization)])

PARAM_STREAM_ID = Path(None, alias='stream_id',
                       description='The unique ID of the stream')


@router.post('/{stream_id}', summary='Send data to one or multiple streams')
async def send_data_entries(
        sid: str = PARAM_STREAM_ID,
        entries: list[UploadFile] | None = File(..., description='A list of data entries (as multiform files) to be added into the stream(s).')):
    """Send data into one or multiple streams using multipart/form-data,
    each part represent a separate entry of a stream. Set
    **stream_id** to `*` to upload data to multiple streams. In this
    case, the **filename** field of the multipart header will be used as
    stream ids.

    """
    filenames = map(lambda x: x.filename, entries)
    streams = filenames if sid=='*' else itertools.repeat(sid)
    data = await asyncio.gather(*map(lambda x: x.read(), entries))
    res = await DataStream.addEntries(zip(streams, data))
    return res

@router.get('/{stream_id}', summary='Retrieve data from one or multiple streams', response_class=StreamingResponse)
async def get_data_entries(
        sid: str = PARAM_STREAM_ID,
        last_entry_id: str | None = Query('*', description="Only retrieve entries later than the provided ID"),
        count:  int | None = Query(1, description="The maximum number of elements to be returned")):
    """This retrieves **count** elements that have later timestamps
    than **last_entry_id** from the specified data stream. The entry
    ID should be in the form of:

    `<millisecondsTime>-<sequenceNumber>` 

    More info can be found on [Redis's
    documentation](https://redis.io/docs/manual/data-types/streams/#entry-ids). Special
    IDs such as `0` and `$` are also accepted. In addition, if
    **last_entry_id** is a `*`, the latest **count** entries will be
    returned.

    If successful, the response header will include an `entry-offset`
    field describing the offsets of the batch
    `[[stream_id,entry_id,offset],...]` in JSON format.

    This can also be used to retrieve data from multiple streams. To
    do so, set **stream_id** to a list of stream IDs separated by
    `+`. For example, to retrieve data from `main` and `depth` stream,
    set **stream_id** to `main+depth`. This means that stream id must
    not contain the `+` sign. When multiple streams are specified,
    **last_entry_id** could be set specifically for each stream using
    the similar `+` separator (e.g. **last_entry_id**=`$+$`), or for
    the all streams (e.g. just `$`).

    """
    streams = dict(zip(sid.split('+'),itertools.cycle(re.split('\\+| ', last_entry_id))))
    try:
        entries = await DataStream.getEntries(streams, count)
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err))
    offsets, content = unzip_entries(entries)
    return StreamingResponse(io.BytesIO(content),
                             headers={'entry-offset': offsets},
                             media_type='application/octet-stream')

@router.websocket('/{stream_id}/push')
async def push_data_ws(
        ws: WebSocket,
        sid: str = PARAM_STREAM_ID,
        batch:  bool | None = Query(False, description="set to 'true' if entries will be sent in batches (alternate one text, one bytes)"),
        ack: bool | None = Query(False, description="set to 'true' if would like the server to respond to each entry/batch with inserted entry IDs")):
    """
    """
    if not (await UserAuth.authorizeWebSocket(ws)):
        return
    await ws.accept()
    sids = itertools.repeat(sid)
    try:
        while True:
            if batch or sid=='*':
                sids, offsets = zip(*orjson.loads(await ws.receive_text()))
            data = await ws.receive_bytes()
            if batch:
                offsets.append(len(data))
                entries = map(lambda x: data[offsets[x]:offsets[x+1]], range(len(offsets)-1))
            else:
                entries = [data]
            res = await DataStream.addEntries(zip(sids, entries))
            if ack:
                ids = ','.join(map(lambda x: x.decode('utf-8'), res))
                await ws.send_text(ids)
    except (WebSocketDisconnect, ConnectionClosed):
        pass


@router.websocket('/{stream_id}/pull')
async def pull_data_ws(
        ws: WebSocket,
        sid: str = PARAM_STREAM_ID,
        count:  int | None = Query(1, description="the maximum number of entries for each receive"),
        last_entry_id: str | None = Query('$', description="Start retrieving entries laters than the provided ID")):
    """
    """
    if not (await UserAuth.authorizeWebSocket(ws)):
        return
    await ws.accept()
    try:
        last = dict(zip(sid.split('+'),itertools.cycle(re.split('\\+| ', last_entry_id))))
        while True:
            entries = await DataStream.getEntries(last, count, block=10000)
            if entries:
                offsets, content = unzip_entries(entries)
                await ws.send_text(offsets)
                await ws.send_bytes(content)
                for sid,data in entries:
                    sid = sid.decode('utf-8') if isinstance(sid, bytes) else sid
                    last[sid] = data[-1][0]

    except (WebSocketDisconnect, ConnectionClosed):
        pass
        

@router.post('/hololens', summary='Send data to a stream')
async def send_any_hololens_entries(
        entries: list[UploadFile] | None = File(..., description='A list of data entries (as multiform files) to be added into the stream(s).')):
    res = await DataStream.addEntries([
        (sid, d)
        for e in entries
        for sid, d in holoframe.load_streams(e)
    ])
    return res