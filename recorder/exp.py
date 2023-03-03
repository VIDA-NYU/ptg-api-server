import os
import json
import websockets
from contextlib import asynccontextmanager

class BaseRecorder:
    def __init__(self, url=None):
        self._url = url or os.getenv('REDIS_WEBSOCKET_URL') or 'ws://localhost:8000'

    @asynccontextmanager
    async def receiver(sid: str):
        async with websockets.connect(f'{self._url}/data/{sid}/pull', max_size=None) as ws:
            async def recv():
                while True:
                    # read the header and data
                    header = json.loads(await ws.recv())
                    entries = await ws.recv()
                    # break up chunks
                    for dm1, d in zip([{}] + header, header):
                        yield d, entries[dm1.get('offset', 0):d.get('offset')]
            yield recv

    async def _run(self, sid: str):
        try:
            async with self.receiver(sid) as recv:
                async for d, x in recv():
                    await self.handle_message(d, x)
        finally:
            await self.handle_close()

    async def handle_message(self, d, x):
        if self._file is None:
            self._file = await self.open_file(d, x)
        should_close = await self.write(d, x)
        if should_close:
            await self.handle_close()

    async def handle_close(self):
        if self._file is not None:
            await self.close_file()
            self._file = None



    async def open_file(self, d, x):
        pass

    async def write(self, d, x):
        pass

    async def close_file(self):
        pass


class BufferedRecorder(BaseRecorder):
    def __init__(self, name, store_dir='', max_len=1000, max_size=9.5*MB, **kw):
        super().__init__(**kw)
        self.out_dir = os.path.join(store_dir, name)
        os.makedirs(self.out_dir, exist_ok=True)
        self.name = name
        self.max_len = max_len
        self.max_size = max_size

    async def open_file(self, d, x):
        self.size = 0
        return []

    async def write(self, meta, data):
        self.size += len(data)
        self._file.append([meta['ts'], data])
        return (self.max_len and len(self._file) >= self.max_len) or (self.max_size and self.size >= self.max_size)

    async def close_file(self):
        self._file, buffer = None, self._file
        loop = asyncio.get_running_loop()
        asyncio.ensure_future(loop.run_in_executor(None, self.dump, buffer))

    def dump(self, buffer):
        raise NotImplementedError



MB = 1024 * 1024

class RawRecorder(BaseRecorder):
    def __init__(self, name, store_dir='', max_len=1000, max_size=9.5*MB, **kw):
        super().__init__(max_len=max_len, max_size=max_size, **kw)
        self.out_dir = os.path.join(store_dir, name)
        os.makedirs(self.out_dir, exist_ok=True)
        self.name = name
        self.max_len = max_len
        self.max_size = max_size

    async def open_file(self, d, x):
        self.size = 0
        return zipfile.ZipFile(fname, 'a', zipfile.ZIP_STORED, False)

    async def write(self, meta, data):
        self.size += len(data)
        self._file.writestr(meta['ts'], d)
        return (self.max_len and len(self._file) >= self.max_len) or (self.max_size and self.size >= self.max_size)

    async def close_file(self):
        self._file.close()


class VideoWriter(BaseRecorder):
    def __init__(self, name, store_dir, sample, t_start, fps=15, vcodec='libx264', crf='23', scale=None, norm=None, max_duplicate_secs=10,  **kw):
        super().__init__(**kw)
        self.fname = fname = os.path.join(store_dir, f'{name}.mp4')
        self.scale = scale
        self.norm = norm
        
        self.prev_im = self.dump(sample['image'])
        self.t_start = t_start
        h, w = sample['image'].shape[:2]

        self.fps = fps
        self.max_duplicate = max_duplicate_secs * fps
        self.cmd = (
            f'ffmpeg -y -s {w}x{h} -pixel_format bgr24 -f rawvideo -r {fps} '
            f'-i pipe: -vcodec {vcodec} -pix_fmt yuv420p -crf {crf} {fname}')

    def context(self):
        import subprocess, shlex, sys
        process = subprocess.Popen(shlex.split(self.cmd),  stdin=subprocess.PIPE,  stdout=subprocess.PIPE)
        self.writer = process.stdin

        self.t = 0
        try:
            print("Opening video ffmpeg process:", self.cmd)
            yield self
        except BrokenPipeError as e:
            print(f"Broken pipe writing video: {e}")
            if process.stderr:
                print(process.stderr.read())
            raise e
        finally:
            print('finishing')
            if process.stdin:
                process.stdin.close()
            process.wait()
            print('finished', self.fname)

    def write(self, data, ts=None):
        im = self.dump(data['image'])
        if ts is not None:
            while self.t < ts - self.t_start:
                self.writer.write(self.prev_im)
                self.t += 1.0 / self.fps
            self.prev_im = im
        self.writer.write(im)
        self.t += 1.0 / self.fps

    def dump(self, im):
        if self.scale:
            im = (im * self.scale).astype(im.dtype)
        if self.norm:
            im = im / im.max()

        # convert int32 to uint8
        if not np.issubdtype(im.dtype, np.uint8):
            if np.issubdtype(im.dtype, np.integer):
                im = im.astype(float) / np.iinfo(im.dtype).max
            im = (im * 255).astype(np.uint8)
        if im.ndim == 2:
            im = np.broadcast_to(im[:,:,None], im.shape+(3,))
        return im[:,:,::-1].tobytes()

