import os
import asyncio
import io
import itertools
import orjson
import re
import numpy as np
from fastapi import APIRouter, Depends, Query, Path, HTTPException, File, Request, Response, Header, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from websockets.exceptions import ConnectionClosed
from app.auth import UserAuth
# from app.store import DataStream
from app.core.streams import Streams
from app.utils import get_tag_names, pack_entries
from app import utils
from app.core import holoframe, converters

STREAM_STORE = Streams()

tags = [
    {
        'name': 'mjpeg',
        'description': 'Send and receive data through the streams created with the "streams" endpoints'
    }
]
router = APIRouter(prefix='/mjpeg', tags=get_tag_names(tags),
                   #dependencies=[Depends(UserAuth.require_authorization)]
)

PARAM_STREAM_ID = Path(None, alias='stream_id', description='The unique ID of the stream')
PARAM_LAST_ENTRY_ID = Query('$', description="Start retrieving entries later than the provided ID")
PARAM_COUNT = Query(1, description="the maximum number of entries for each receive")
PARAM_INPUT = Query(None, description="The entry input format. If not provided, the format will be guessed.")
PARAM_OUTPUT = Query(None, description="The entry output format. Use this if you want to convert to a different format - e.g. jpg, png, json.")
PARAM_PARSE_META = Query(False, description='Try to parse frame as a hololens format to get the timestamp.')
PARAM_TIME_SYNC_ID = Query(None, description="the stream ID to synchronize by")


@router.get('/{stream_id}', summary='Retrieve data from one or multiple streams', response_class=StreamingResponse)
async def stream_jpeg_frames(
        sid: str = PARAM_STREAM_ID,
        count:  int | None = PARAM_COUNT,
        last_entry_id: str | None = PARAM_LAST_ENTRY_ID,
        time_sync_id:  str | None = PARAM_TIME_SYNC_ID,
        input: str|None=PARAM_INPUT
    ):
    """mjpeg video stream to an image tag.

    ```
    <img src={`${API_URL}/data/mjpeg/main`} />
    ```
    """
    return StreamingResponse(
        mjpeg_stream(sid, count, last_entry_id, time_sync_id, input), 
        media_type="multipart/x-mixed-replace;boundary=frame")
    

placeholder_fname = 'please-stand-by.jpg'
with open(os.path.join(os.path.dirname(__file__), placeholder_fname), 'rb') as f:
    placeholder_frame = f.read()

black_frame = converters.registry['jpg']().dump(np.zeros((428, 760, 3), dtype=np.uint8))



async def mjpeg_stream(sid, count, last_entry_id, time_sync_id, input):
    yield _toframe(black_frame)

    last = init_last(sid, last_entry_id)
    while True:
        entries = await STREAM_STORE.get_entries(last, count, block=3000)
        if not entries:
            yield _toframe(placeholder_frame)
            continue

        for sid, data in convert_entries(entries, 'jpg', input):
            for ts, frame in data:
                yield _toframe(frame[b'd'])
        last = update_last(last, entries, time_sync_id)


def _toframe(frame, ct='image/jpeg'):
    return b'--frame\r\nContent-Type: {ct}\r\n\r\n' + frame + b'\r\n'


def init_last(sid, last_entry_id):
    return dict(zip(
        sid.split('+'),
        itertools.cycle(re.split('\\+| ', last_entry_id))
    ))

def update_last(last, entries, time_sync_id=None):
    # use one stream id as time keeper
    entries = [[sid.decode('utf-8') if isinstance(sid, bytes) else sid, data] for sid, data in entries]
    if time_sync_id:
        last_ts = next((d[-1][0] for sid, d in entries if sid == time_sync_id))
        if not last_ts:
            return last
        for sid, data in entries:
            last[sid] = last_ts

    for sid, data in entries:
        last[sid] = data[-1][0]
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



import mimetypes
from app.core.recordings import RECORDING_POST_PATH


CHUNK_SIZE = 1024*1024

@router.get("/chunked/{file_path:path}", summary='stream recording video')
async def video_endpoint(file_path: str, range: str = Header(None)):
    file_path = os.path.join(RECORDING_POST_PATH, file_path)
    start, end = range.replace("bytes=", "").split("-")
    start = int(start)
    end = int(end) if end else start + CHUNK_SIZE
    total = os.stat(file_path).st_size
    print(start, end, total, 1.*(end-start)/total, flush=True)
    with open(file_path, "rb") as f:
        f.seek(start)
        data = f.read(end - start)
        print(len(data), flush=True)

        return Response(
            data,
            status_code=206,
            headers={
                'Content-Range': f'bytes {start}-{end}/{total}',
                'Accept-Ranges': 'bytes'
            },
            media_type=mimetypes.guess_type(file_path)[0] or "video/mp4")




