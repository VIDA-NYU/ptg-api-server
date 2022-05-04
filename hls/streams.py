import os
import sys
import asyncio
import redis.asyncio as aioredis

red = aioredis.from_url(os.getenv('REDIS_URL') or 'redis://127.0.0.1:6379')

HLS_URL = os.getenv('HLS_URL') or 'localhost:1936'


async def stream_async(sid='webcam:pv', count=1, last='$', timeout=10000):
    '''Stream redis to stdout.'''
    while True:
        entries = await get_entries(sid, count, last, timeout)
        if not entries:
            print('no entries. trying again')
            continue
        last, frame = entries[-1]
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
        last, frame = entries[-1]
        im = np.array(Image.open(io.BytesIO(frame[b'd'])))
        cv2.imshow('stream', im[:,:,::-1])
        cv2.waitKey(1)

def show_stream(*a, **kw): return asyncio.run(show_stream_async(*a, **kw))


async def push_webcam_hls_async(src=0, sid='webcam:pv'):
    '''Push webcam directly to hls server'''
    import cv2
    from PIL import Image

    cap = cv2.VideoCapture(src)
    async with HLSStreamer(HLS_URL, sid) as hls:
        while True:
            rc = hls.proc.returncode
            if rc is not None:
                if rc:
                    raise RuntimeError(f'ffmpeg exit code {rc}')
                return
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


if __name__ == '__main__':
    import fire
    fire.Fire()