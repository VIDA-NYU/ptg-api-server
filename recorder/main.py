'''Record data from the API to file. PARTIALLY DEVELOPED / UNTESTED


'''
import os
import io
import glob
import time
import datetime
import asyncio
import tqdm
import redis.asyncio as aioredis

import ptgctl
import ptgctl.tools.local_record_convert2 as lrc


def tqprint(*a, **kw):
    tqdm.tqdm.write(' '.join(map(str, a)), **kw)

def parse_time(tid: str):
    '''Convert a redis timestamp to a datetime object.'''
    return datetime.datetime.fromtimestamp(parse_epoch_time(tid))

def parse_epoch_time(tid: str):
    '''Convert a redis timestamp to epoch seconds.'''
    return int(tid.split('-')[0])/1000


RAW_PATH = 'data/raw'
POST_PATH = 'data/post'


class Disk:
    EXT = '.zip'
    def __init__(self, *fs, path='./data/raw'):
        self.path = os.path.join(path, *fs)
        os.makedirs(self.path, exist_ok=True)

    def list(self, stream_id):
        return sorted(glob.glob(os.path.join(self.path, stream_id, f'**/*{self.EXT or ""}')))

    def store(self, entries, stream_id):
        fname, archive = _zip(entries)
        fname = os.path.join(self.path, stream_id, fname)
        os.makedirs(os.path.dirname(fname), exist_ok=True)
        with open(fname, 'wb') as f:
            f.write(archive)
        tqprint(
            'wrote', fname, len(entries), _pretty_bytes(len(archive)), 
            parse_time(entries[0][0]).strftime('%X.%f'), 
            parse_time(entries[-1][0]).strftime('%X.%f'))

    def load(self, fname, **kw):
        with open(fname, 'rb') as f:
            for ts, data in _unzip(f.read(), **kw):
                yield ts, data


def _pretty_bytes(b, scale=1000, names=['b', 'kb', 'mb', 'gb', 'tb']):
    return next((
            f'{b / (scale**i):.1f}{n}' 
            for i, n in enumerate(names) 
            if b / (scale**(i+1)) < 1
        ), 
        f'{b / (scale**(len(names)-1))}{names[-1]}')


WRITERS = {
    'disk': Disk,
}

def get_writer(name='disk', *a, **kw):
    return WRITERS[name](*a, **kw)


def _zip(entries):
    import zipfile
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_STORED, False) as zf:
        for ts, data in entries:
            zf.writestr(ts, data)
    #date = parse_time(entries[0][0]).strftime('%Y-%m-%d')
    fn = f'{entries[0][0]}_{entries[-1][0]}.zip'
    return fn, archive.getvalue()


def _unzip(data, name_only=False):
    import zipfile
    archive = io.BytesIO(data)
    with zipfile.ZipFile(archive, 'r', zipfile.ZIP_STORED, False) as zf:
        for ts in sorted(zf.namelist()):
            if name_only:
                yield ts
                continue
            
            with zf.open(ts, 'r') as f:
                data = f.read()
                yield ts, data



MB = 1024 * 1024


class Recorder:
    def __init__(self, batches=None, url=None, recording_id_key='recording:id'):
        self.url = url or os.getenv('REDIS_URL') or 'redis://localhost:6379'
        self.recording_id_key = recording_id_key
        self.batches = batches

    async def connect(self):
        self.redis = await aioredis.from_url(self.url)

    async def stream_ids(self):
        return [x.decode('utf-8') async for x in self.redis.scan_iter(_type='stream')]

    async def get_id(self):
        rec_id = await self.redis.get(self.recording_id_key)
        return rec_id.decode('utf-8') if rec_id else rec_id

    async def start_recording(self, rec_id=None):
        rec_id = rec_id or str(int(time.time() * 1000))
        await self.redis.set(self.recording_id_key, rec_id)
        return rec_id

    async def stop_recording(self):
        return await self.redis.delete(self.recording_id_key)

    async def wait_for_recording_id(self, initial_id=None, delay=1):
        while True:
            self.rec_id = rec_id = await self.get_id()
            if rec_id != initial_id:
                return rec_id
            await asyncio.sleep(delay)

    async def run(self):
        while True:
            try:
                print('waiting for recording')
                # wait for a recording ID
                rec_id = await self.wait_for_recording_id()
                batches = self.batches or [await self.stream_ids()]
                # batches = self.batches or [[sid] for sid in await self.stream_ids()]
                await asyncio.gather(
                    # continually check the recording ID, while its still the same
                    self.wait_for_recording_id(rec_id),
                    # record batches while 
                    *(self.record_async(rec_id, *sids) for sids in batches))
            except Exception:
                import traceback
                traceback.print_exc()
                await asyncio.sleep(5)

    async def record_async(self, rec_id, *sids, raw_path=RAW_PATH, post_path=POST_PATH, max_size=9.5 * MB, max_len=1000, batch_size=16, block=5000, last='$'):
        print('starting recording', rec_id)
        redis = self.redis

        drive = get_writer('disk', rec_id or '', path=raw_path)
        acc = Batches({s: last for s in sids}, max_len, max_size)
        try:
            # get the last bit of calibration data
            cal_sids = [s for s in sids if s.lower().endswith('cal') and s[:-3] in sids]
            async with redis.pipeline() as p:
                for sid in cal_sids:
                    p.xrevrange(sid, '+', '-', count=1)
                streams = list(zip(cal_sids, await p.execute()))
                for sid, data in streams:
                    print('calibration:', sid, len(data))
                acc.update(streams)

            # watch that the recording ID is still the same
            while self.rec_id and self.rec_id == rec_id:
                # get the next batch of streams
                streams = await redis.xread(streams=acc.last, count=batch_size, block=block)
                # add entries to stream batches
                acc.update(streams)
                # as they finish, they will emit entries here
                for sid, entries in acc.finished():
                    drive.store(entries, sid)
        finally:
            for sid, entries in acc.entries.items():
                drive.store(entries, sid)
            acc.close()
            print()
            print('done recording', rec_id, flush=True)
            lrc.convert(os.path.join(raw_path, rec_id), out_path=post_path)



class Batches:
    def __init__(self, last, max_len=1000, max_size=9.5 * MB):
        self.max_len = max_len
        self.max_size = max_size
        self.entries = {}
        self.size = {}
        self.last = last
        self.pbars = {}

    def update(self, streams):
        for sid, entries in streams:
            sid = sid.decode('utf-8') if isinstance(sid, bytes) else sid
            if sid not in self.entries:
                self.size[sid] = 0
                self.entries[sid] = []
                self.pbars[sid] = tqdm.tqdm(total=self.max_len, desc=sid)

            self.size[sid] += sum(len(x[b'd']) for _, x in entries)
            self.entries[sid].extend((ts.decode('utf-8'), x[b'd']) for ts, x in entries)
            self.last[sid] = last = entries[-1][0]
            self.pbars[sid].update(len(entries))
            self.pbars[sid].set_description(f'{sid} {last} {datetime.datetime.now() - parse_time(last.decode("utf-8"))}')

    def is_done(self, sid):
        return len(self.entries[sid]) >= self.max_len or self.size[sid] >= self.max_size

    def finished(self):
        for sid, entries in self.entries.items():
            if self.is_done(sid):
                yield sid, entries
                self.size[sid] = 0
                self.entries[sid] = []
                self.pbars[sid].reset()

    def close(self):
        for sid, pbar in self.pbars.items():
            pbar.close()
        self.pbars = {}
        self.entries = {}
        self.size = {}



def async_wrap(func):
    import functools
    @functools.wraps(func)
    def inner(*a, **kw):
        return asyncio.run(func(*a, **kw))
    inner.asyncio = func
    return inner


@async_wrap
async def run():
    rec = Recorder()
    await rec.connect()
    await rec.run()

@async_wrap
async def start():
    rec = Recorder()
    await rec.connect()
    print(await rec.start_recording())

@async_wrap
async def stop():
    rec = Recorder()
    await rec.connect()
    print(await rec.stop_recording())


if __name__ == '__main__':
    funcs = [run, start, stop]
    import fire
    fire.Fire({f.__name__: f for f in funcs})
