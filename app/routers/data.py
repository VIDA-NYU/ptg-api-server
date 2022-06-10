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
from app.core.streams import Streams
from app.utils import get_tag_names, unzip_entries, prints_traceback
from app import utils
from app.core import holoframe

STREAM_STORE = Streams()

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

PARAM_PARSE_META = Query(False, description='Try to parse frame as a hololens format to get the timestamp.')


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
    streams = [x.filename.split('/') for x in entries] if sid == '*' else [sid] * len(entries)
    data = await asyncio.gather(*(x.read() for x in entries))
    
    if parse_meta:
        metas = [holoframe.load(d) for d in data]
        ts = [d.get('time') for d in metas]
    else:
        ts = [None] * len(data)
    return await STREAM_STORE.add_entries(zip(streams, ts, data))


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
    streams = dict(zip(
        sid.split('+'),
        itertools.cycle(re.split('\\+| ', last_entry_id))
    ))
    try:
        entries = await STREAM_STORE.get_entries(streams, count)
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
        ack: bool | None = Query(False, description="set to 'true' if would like the server to respond to each entry/batch with inserted entry IDs"),
        parse_meta: bool=PARAM_PARSE_META):
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
            entries = [data[i:j] for i, j in zip(offsets, offsets[1:] + [None])] if batch else [data]

            if parse_meta:
                metas = [holoframe.load(d) for d in entries]
                ts = [d.get('time') for d in metas]
            else:
                ts = [None] * len(entries)

            res = await STREAM_STORE.add_entries(zip(sids, ts, entries))
            if ack:
                await ws.send_text(','.join(x.decode('utf-8') for x in res))
    except (WebSocketDisconnect, ConnectionClosed):
        pass


@router.websocket('/{stream_id}/pull')
async def pull_data_ws(
        ws: WebSocket,
        sid: str = PARAM_STREAM_ID,
        count:  int | None = Query(1, description="the maximum number of entries for each receive"),
        last_entry_id: str | None = Query('$', description="Start retrieving entries laters than the provided ID"),
        time_sync_id:  str | None = Query(None, description="the maximum number of entries for each receive"),

    ):
    """
    """
    if not (await UserAuth.authorizeWebSocket(ws)):
        return
    await ws.accept()
    try:
        last = dict(zip(
            sid.split('+'),
            itertools.cycle(re.split('\\+| ', last_entry_id))
        ))
        while True:
            entries = await STREAM_STORE.get_entries(last, count, block=10000)
            if entries:
                offsets, content = unzip_entries(entries)
                await ws.send_text(offsets)
                await ws.send_bytes(content)
                # use one stream id as time keeper
                if time_sync_id:
                    last_ts = next((d[-1][0] for sid, d in entries if sid == time_sync_id))
                    if not last_ts:
                        raise HTTPException(status=500)
                    for sid, data in entries:
                        last[sid] = last_ts
                else:
                    for sid, data in entries:
                        sid = sid.decode('utf-8') if isinstance(sid, bytes) else sid
                        last[sid] = data[-1][0]

    except (WebSocketDisconnect, ConnectionClosed):
        pass


import time
class TimeTracker:
    def __init__(self, time_sync_id: str=None, realtime: bool=False):  # , always_latest: bool=False
        self.last = {}
        self.time_sync_id = time_sync_id
        self.realtime = realtime
        # self.always_latest = always_latest

    def _get_last_times(self, entries):
        return {
            sid.decode('utf-8') if isinstance(sid, bytes) else sid: d[-1][0]
            for sid, d in entries
        }

    def update(self, entries):
        times = self._get_last_times(entries)
        # if self.always_latest:
        #     return self._update_realtime(times)
        # use a single stream as time keeper
        if self.time_sync_id:
            times = self._time_sync(times)
        # process in realtime
        elif self.realtime:
            times = self._update_realtime(times)
        # 
        self._update_independent(times)

    def _update_independent(self, times):
        self.last.update(times)

    def _time_sync(self, times):
        if self.time_sync_id not in times:
            raise NotImplementedError
        t = times[self.time_sync_id]
        return {k: t for k in times}

    last_time = None
    def _update_realtime(self, times):
        t = time.time()
        if self.last_time is None:
            self.last_time = t
        dt = t - self.last_time
        times = {
            sid: utils.parse_epoch_ts(ts) + dt
            for sid, ts in times.items()
        }
        self.last_time = t
        return times

    # def _update_request(self, last=None):
    #     if last is not None:
    #         if not isinstance(last, dict):
    #             pass
            

    # def _update_always_latest(self, times):
    #     self.last.update({k: '$' for k in times})
