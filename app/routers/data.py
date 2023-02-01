import time
import asyncio
import io
import itertools
import orjson
import re
from fastapi import APIRouter, Depends, Query, Path, HTTPException, File, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from websockets.exceptions import ConnectionClosed
from app.auth import UserAuth
# from app.store import DataStream
from app.core.streams import Streams, MultiStreamCursor
from app.utils import get_tag_names, pack_entries
from app import utils
from app.core import holoframe, converters

STREAM_STORE = Streams()

tags = [
    {
        'name': 'data',
        'description': 'Send and receive data through the streams created with the "streams" endpoints'
    }
]
router = APIRouter(prefix='/data', tags=get_tag_names(tags),
                   dependencies=[Depends(UserAuth.require_authorization)])

PARAM_STREAM_ID = Path(None, alias='stream_id', description='The unique ID of the stream')
PARAM_LAST_ENTRY_ID = Query('*', description="Start retrieving entries later than the provided ID")
PARAM_LAST_ENTRY_ID_BLOCK = Query('$', description="Start retrieving entries later than the provided ID")
PARAM_COUNT = Query(1, description="the maximum number of entries for each receive")
PARAM_INPUT = Query(None, description="The entry input format. If not provided, the format will be guessed.")
PARAM_OUTPUT = Query(None, description="The entry output format. Use this if you want to convert to a different format - e.g. jpg, png, json.")
PARAM_PARSE_META = Query(False, description='Try to parse frame as a hololens format to get the timestamp.')
PARAM_TIME_SYNC_ID = Query(None, description="the stream ID to synchronize by")

@router.post('/{stream_id}', summary='Send data to one or multiple streams')
async def send_data_entries(
        sid: str = PARAM_STREAM_ID,
        entries: list[UploadFile] | None = File(..., description='A list of data entries (as multiform files) to be added into the stream(s).'),
        parse_meta=PARAM_PARSE_META):
    """Send data into one or multiple streams using multipart/form-data,
    each part represent a separate entry of a stream. Set
    **stream_id** to `*` to upload data to multiple streams. In this
    case, the **filename** field of the multipart header will be used as
    stream ids.

    """
    sids = [x.filename.split('/') for x in entries] if sid == '*' else [sid] * len(entries)
    data = await asyncio.gather(*(x.read() for x in entries))
    ts = get_ts(data, parse_meta)

    return await STREAM_STORE.add_entries(zip(sids, ts, data))


@router.get('/{stream_id}', summary='Retrieve data from one or multiple streams', response_class=StreamingResponse)
async def get_data_entries(
        sid: str = PARAM_STREAM_ID,
        last_entry_id: str | None = PARAM_LAST_ENTRY_ID,
        count:  int | None = PARAM_COUNT,
        input: str | None=PARAM_INPUT, output: str | None=PARAM_OUTPUT,
    ):
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
    entries = await STREAM_STORE.get_entries(init_last(sid, last_entry_id), count)
    if output:
        entries = convert_entries(entries, output, input)
    offsets, content = pack_entries(entries)
    return StreamingResponse(io.BytesIO(content),
                             headers={'entry-offset': offsets},
                             media_type='application/octet-stream')


@router.websocket('/{stream_id}/push')
async def push_data_ws(
        ws: WebSocket,
        sid: str = PARAM_STREAM_ID,
        batch:  bool | None = Query(None, description="set to 'true' if entries will be sent in batches (alternate one text, one bytes)"),
        ack: bool | None = Query(False, description="set to 'true' if would like the server to respond to each entry/batch with inserted entry IDs"),
        parse_meta: bool=PARAM_PARSE_META):
    """
    """
    if not (await UserAuth.authorizeWebSocket(ws)):
        return
    await ws.accept()
    
    sids = None
    if sid == '*':
        assert batch
    elif '+' in sid:
        assert batch
        sids = sid.split('+')
    else:
        sids = itertools.repeat(sid)
    try:
        while True:
            ts = None
            if batch:
                offsets = orjson.loads(await ws.receive_text())
                if offsets and isinstance(offsets[0], list):
                    if len(offsets[0]) == 3:
                        sids, ts, offsets = zip(*offsets)
                    else:
                        sids, offsets = zip(*offsets)
                elif sids is None:
                    raise ValueError("You must upload the sid with the offsets if using sid='*'")
            data = await ws.receive_bytes()
            if not offsets or offsets[0] != 0:
                offsets = (0,)+tuple(offsets)
            entries = [data[i:j] for i, j in zip(offsets, offsets[1:])] if batch else [data]
            ts = ts or get_ts(entries, parse_meta)

            res = await STREAM_STORE.add_entries(zip(sids, ts, entries))
            if ack:
                await ws.send_text(','.join(x.decode('utf-8') for x in res))
    except (WebSocketDisconnect, ConnectionClosed):
        import traceback
        traceback.print_exc()
        print("(WebSocketDisconnect, ConnectionClosed)")


@router.websocket('/{stream_id}/pull')
async def pull_data_ws(
        ws: WebSocket,
        sid: str = PARAM_STREAM_ID,
        count:  int | None = PARAM_COUNT,
        last_entry_id: str | None = PARAM_LAST_ENTRY_ID_BLOCK,
        time_sync_id:  int | str | None = PARAM_TIME_SYNC_ID,
        latest: bool|None=Query(None, description="should we return all data points or just the latest? This is True unless you provide an absolute timestamp with last_entry_id"),
        timeout: int|None=None,
        onebyone: bool=False,
        rate_limit: float|None=Query(None, description="Rate limit the output of data (in seconds per iteration)."),
        input: str|None=PARAM_INPUT, output: str|None=PARAM_OUTPUT,
        ack: bool | None = Query(False, description="set to 'true' to wait for the client to send an acknowledgement message (of any content) before sending more data"),
    ):
    """
    """
    if not (await UserAuth.authorizeWebSocket(ws)):
        return
    await ws.accept()
    try:
        if isinstance(time_sync_id, int):
            time_sync_id = sid.split('+')[time_sync_id]
        last = init_last(sid, last_entry_id)
        latest = latest if latest is not None else (last_entry_id is None or '$' in last_entry_id or '-' in last_entry_id)
        print(last, latest, flush=True)
        cursor = MultiStreamCursor(last, latest=latest, time_sync_id=time_sync_id, block=timeout or 3000)
        
        tlast = time.time()
        while True:
            entries = await cursor.next()
            if entries:
                entries_batch = [[x] for x in entries] if onebyone else [entries]
                for entries in entries_batch:
                    if output:
                        entries = convert_entries(entries, output, input)
                    offsets, content = pack_entries(entries)
                    await ws.send_text(offsets)
                    await ws.send_bytes(content)
                    if ack:
                        await ws.receive()
                    if rate_limit:
                        tnow=time.time()
                        time.sleep(max(0, rate_limit - (tnow - tlast)))
                        tlast=tnow
            elif timeout:
                break
    except (WebSocketDisconnect, ConnectionClosed):
        pass



async def mjpeg_stream(sid, count, last_entry_id, time_sync_id, input):
    last = init_last(sid, last_entry_id)
    while True:
        entries = await STREAM_STORE.get_entries(last, count, block=10000)
        if entries:
            for sid, data in convert_entries(entries, 'jpg', input):
                for ts, frame in data:
                    yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            last = update_last(last, entries, time_sync_id)


def init_last(sid, last_entry_id):
    d = dict(zip(
        sid.split('+'),
        itertools.cycle(re.split('\\+| ', last_entry_id))
    ))
    #d = {k: '-' if v == '.' else v for k, v in d.items()}
    return d

def update_last(last, entries, time_sync_id=None):
    # use one stream id as time keeper
    entries = [[sid.decode('utf-8') if isinstance(sid, bytes) else sid, data] for sid, data in entries]
    if time_sync_id:
        last_ts = next((d[-1][0] for sid, d in entries if sid == time_sync_id))
        if not last_ts:
            return last
        for sid, data in entries:
            last[sid] = last_ts
        return last

    for sid, data in entries:
        last[sid] = data[-1][0]
    print(last)
    return last

def get_ts(entries, parse_meta=False):
    if parse_meta:
        metas = [holoframe.load(d) for d in entries]
        ts = [d.get('time') for d in metas]
    else:
        ts = [None] * len(entries)
    return ts

def convert_entries(entries, output_format, input_format=None):
    converted = []
    for sid, data in entries:
        cvt = converters.get_converter(output_format, input_format, sid)
        converted.append([sid, [[ts, {**d, b'd': cvt(d[b'd'])}] for ts, d in data]])
    return converted
