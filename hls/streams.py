import os
import sys
import asyncio
import json
import redis.asyncio as aioredis
import cv2

import io
import numpy as np
from PIL import Image

red = aioredis.from_url(os.getenv('REDIS_URL') or 'redis://127.0.0.1:6379')

HLS_URL = os.getenv('HLS_URL') or 'localhost:1936'


async def stream_async(sid='webcam:pv', last='$', timeout=10000):
    '''Stream redis to stdout.'''
    while True:
        entries = await get_entries(sid, 1, last, timeout)
        if not entries:
            print('no entries. trying again')
            continue
        # boxes = await get_entries(f'{sid}:boxes', 1, last, 1)
        last, frame = entries[-1]
        # if boxes:
        #     im = np.array(Image.open(io.BytesIO(frame)))
        #     for b in boxes[-1][1]:
        #         draw_bbox(im, **b)
        #     output = io.BytesIO()
        #     Image.fromarray(im).save(output, format='jpeg')
        #     frame = output.getvalue()
        sys.stdin.write(frame)

def stream(*a, **kw): return asyncio.run(stream_async(*a, **kw))


async def hls_stream_async(sid='webcam:pv', count=1, last='$', timeout=10000):
    '''Stream redis to hls server.'''
    async with HLSStreamer(HLS_URL, sid) as hls:
        while True:
            entries = await get_entries(sid, count, last, timeout)
            if not entries:
                print('no entries. trying again')
                continue
            last, frame = entries[-1]
            hls.stdin.write(frame)

def hls_stream(*a, **kw): return asyncio.run(hls_stream_async(*a, **kw))


async def show_stream_async(sid='webcam:pv', count=1, last='$', timeout=10000):
    '''read frames from redis and show using csv'''
    import io
    import cv2
    import numpy as np
    from PIL import Image
    while True:
        entries = await get_entries(sid, count, last, timeout)
        if not entries:
            print('no entries. trying again')
            continue
        boxes = await get_entries(f'{sid}:boxes', 1, last, 1)
        last, frame = entries[-1]
        im = np.array(Image.open(io.BytesIO(frame[b'd'])))

        if boxes:
            for b in json.loads(boxes[-1][1][b'd']):
                draw_bbox(im, **b)
        
        cv2.imshow('stream', im[:,:,::-1])
        cv2.waitKey(1)

def show_stream(*a, **kw): return asyncio.run(show_stream_async(*a, **kw))


async def push_webcam_hls_async(src=0, sid='webcam:pv'):
    '''Push webcam directly to hls server'''
    import cv2
    from PIL import Image

    cap = cv2.VideoCapture(src)
    async with HLSStreamer(HLS_URL, sid) as hls:
        while not hls.ended():
            ret, im = cap.read()
            if not ret: 
                print('no frame. breaking.')
                break
            hls.stdin.write(np2jpg(im))
            # hls.stdin.write(Image.fromarray(im).tobytes('raw', 'jpeg', 0, 1))

def push_webcam_hls(*a, **kw): return asyncio.run(push_webcam_hls_async(*a, **kw))





class HLSStreamer:
    '''Stream to hls server using ffmpeg process.'''
    def __init__(self, host, sid, app='hls', img_format='mjpeg'):
        self.cmd = f'ffmpeg -y -f image2pipe -c:v {img_format} -i - -c:v libx264 -an -f flv rtmp://{host}/{app}/{sid}'

    async def __aenter__(self):
        self.proc = await asyncio.create_subprocess_shell(
            self.cmd, stdin=asyncio.subprocess.PIPE, stdout=sys.stdout, stderr=sys.stderr)
        self.stdin = self.proc.stdin
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.proc.stdin.close()
        await self.proc.wait()

    def ended(self):
        rc = self.proc.returncode
        if rc is not None:
            if rc:
                raise RuntimeError(f'ffmpeg exit code {rc}')
            return True


async def get_entries(sid: str, count: int, last: str, block: int=None):
    if last=='*':
        return (await red.xrevrange(sid, count=count))[::-1]
    streams = await red.xread(streams={sid:last}, count=count, block=block)
    return streams[0][1] if streams else []



def np2jpg(im):
    import io
    from PIL import Image
    output = io.BytesIO()
    Image.fromarray(im).save(output, format='jpeg')
    return output.getvalue()



def draw_bbox(im, x, y, h, w, label, confidence, color=(0,255,0)):
    iy, ix = im.shape[:2]
    x, y, x2, y2 = (
        int(ix * max(x, 0)), int(iy * max(y, 0)), 
        int(ix * min(x+w, 1)), int(iy * min(y+h, 1)))
    cv2.rectangle(im, (x, y), (x2, y2), color, 2)
    label = f'{label} ({confidence:.03f})' if label and confidence else (label or confidence)
    if label:
        label = str(label)
        cv2.rectangle(im, (x + 4, y - 6), (x + 4 + 2 + 8*len(label), y + 6), color, -1)
        cv2.putText(im, label, (x + 10, y + 2), 0, 0.3, (0, 0, 0))
    return im

if __name__ == '__main__':
    import fire
    fire.Fire()