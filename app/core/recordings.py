import asyncio
import contextlib
import datetime
import glob
import orjson
import os
import time
import shutil
from app.context import Context
from app.core.streams import Streams
from app.core.utils import parse_epoch_ts, parse_ts, format_epoch_ts
from collections import defaultdict
from fastapi import WebSocketDisconnect
from websockets.exceptions import ConnectionClosed

RECORDING_PATH = os.getenv("RECORDING_PATH") or '/data/recordings'
RECORDING_RAW_PATH = os.path.join(RECORDING_PATH, 'raw')
RECORDING_POST_PATH = os.path.join(RECORDING_PATH, 'post')

STREAM_STORE = Streams()


ctx = Context.instance()

fglob = lambda *fs: glob.glob(os.path.join(*fs))

def safe_listdir(d):
    return os.listdir(d) if os.path.exists(d) else []

class Recordings:
    recording_id_key='recording:id'
    SID = 'event:recording:id'
    def list_recordings(self):
        fs = fglob(RECORDING_RAW_PATH, '*')
        return [os.path.basename(f) for f in fs]

    async def list_recording_info(self, cache=True):
        if cache:
            async with ctx.redis.pipeline() as pipe:
                recordings = self.list_recordings()
                for rid in recordings:
                    pipe.get(f'recording:info:{rid}')
                infos = await pipe.execute()
                for i, (rid, x) in enumerate(zip(recordings, infos)):
                    if not x:
                        infos[i] = x = self.get_recording_info(rid)
                        if x['last-entry'] and (time.time() - parse_epoch_ts(x['last-entry'])) > 3 * 60:
                            pipe.set(f'recording:info:{rid}', orjson.dumps(x))
                    else:
                        infos[i] = x = orjson.loads(x)
                        x['_cached'] = True
                await pipe.execute()
                return infos
        return [self.get_recording_info(rid) for rid in self.list_recordings()]

    async def clear_recording_info_cache(self):
        async with ctx.redis.pipeline() as pipe:
            for rid in self.list_recordings():
                pipe.delete(f'recording:info:{rid}')
                return await pipe.execute()

    async def get_current_recording(self, info=False):
        rid = await ctx.redis.get(self.recording_id_key)
        rid = rid.decode('utf-8') if rid else rid
        if info:
            return self.get_recording_info(rid) if rid else None
        return rid

    def get_recording_info(self, rec_id):
        if rec_id == 'undefined':
            return {"warning": "recording id is undefined"}  # 
        stream_dirs = fglob(RECORDING_RAW_PATH, rec_id, '*')
        streams = [os.path.basename(f) for f in stream_dirs]
        stream_info = {k: self.get_stream_info(rec_id, k) for k in streams}
        return {
            "name": rec_id, 
            "streams": stream_info,
            "size_mb": sum(d['size_mb'] or 0 for d in stream_info.values()),
            **self.first_last_times(*zip(*(
                (d['first-entry'], d['last-entry'])
                for sid, d in stream_info.items()
                if not sid.endswith('Cal')
            ))),
            "files": safe_listdir(os.path.join(RECORDING_POST_PATH, rec_id)),
        }

    def get_stream_info(self, rec_id, name):
        fs = sorted(fglob(RECORDING_RAW_PATH, rec_id, name, '*'))
        return {
            "chunk_count": len(fs),
            "size_mb": sum(os.path.getsize(f) / (1024.**2) for f in fs),
            **self.first_last_times(*zip(*(
                os.path.splitext(os.path.basename(f))[0].split('_') 
                for f in fs
            ))),
        }

    def first_last_times(self, firsts=None, lasts=None):
        first = min((t for t in firsts or () if t), default=None)
        last = max((t for t in lasts or () if t), default=None)
        duration = datetime.timedelta(seconds=parse_epoch_ts(last) - parse_epoch_ts(first)) if first and last else None
        return {
            "duration": str(duration) if duration else None,
            "duration_secs": duration.total_seconds() if duration else None,
            "first-entry": first,
            "last-entry": last,
            "first-entry-time": parse_ts(first).strftime("%c") if first else None,
            "last-entry-time": parse_ts(last).strftime("%c") if last else None,
        }

    def create_recording_id(self, dt_sep='-', sep='.'):
        #return f"rec-at-{str(int(time.time()))}"
        return datetime.datetime.now().strftime(f"%Y{sep}%m{sep}%d{dt_sep}%H{sep}%M{sep}%S")

    async def start(self, rec_id=None):
        rec_id = rec_id or self.create_recording_id()
        is_set = await ctx.redis.set(self.recording_id_key, rec_id)
        if not is_set:
            raise RuntimeError(f"Recording {rec_id} didn't start.")
        await STREAM_STORE.add_entries([(self.SID, None, rec_id.encode('utf-8'))])
        return rec_id

    async def stop(self):
        x = await ctx.redis.delete(self.recording_id_key)
        await STREAM_STORE.add_entries([(self.SID, None, ''.encode('utf-8'))])
        return x

    def rename_recording(self, old_name, new_name):
        raw_old_path = safe_subdir(RECORDING_RAW_PATH, old_name)
        raw_new_path = safe_subdir(RECORDING_RAW_PATH, new_name)
        if os.path.exists(raw_new_path):
            raise OSError(f"Recording {new_name} already exists!")
        if os.path.exists(raw_old_path):
            os.rename(raw_old_path, raw_new_path)
        print(os.path.exists(raw_old_path), raw_old_path, raw_new_path, flush=True)

        post_old_path = safe_subdir(RECORDING_POST_PATH, old_name)
        post_new_path = safe_subdir(RECORDING_POST_PATH, new_name)
        if os.path.exists(post_old_path):
            os.rename(post_old_path, post_new_path)
        print(os.path.exists(post_old_path), post_old_path, post_new_path, flush=True)
        return os.path.exists(raw_new_path), not os.path.exists(raw_old_path)

    def delete_recording(self, name):
        raw_path = safe_subdir(RECORDING_RAW_PATH, name)
        if os.path.exists(raw_path):
            shutil.rmtree(raw_path)
        post_path = safe_subdir(RECORDING_POST_PATH, name)
        if os.path.exists(post_path):
            shutil.rmtree(post_path)
        return not os.path.exists(raw_path), not os.path.exists(post_path)


def safe_subdir(root, name):
    name = os.path.normpath(f'/{name}').strip('/')
    root = os.path.normpath(os.path.abspath(root))
    path = os.path.normpath(os.path.abspath(os.path.join(root, name)))
    assert os.path.commonprefix([root, path]) == root and root != path
    return path

class RecordingPlayer:

    def __init__(self):
        self.reset()

    def reset(self):
        self.done = asyncio.Event()
        self.active = set()
        self.counter = defaultdict(int)
        self.durations = {}
        self.t_current = {}

    def clear_counter(self):
        self.counter.clear()

    def update_counter(self, sid):
        self.counter[sid] += 1

    def get_progress_json(self):
        progress = {
            'updates': dict(self.counter), 
            'active': list(self.active),
            'durations': self.durations,
            'current': self.t_current,
        }
        return orjson.dumps(progress).decode('utf-8')

    def is_done(self):
        return self.done.is_set()

    def set_inactive(self, name):
        self.active.discard(name)

    async def replay_progress(self, ws, update_interval=1):
        try:
            while len(self.active)>0:
                await asyncio.sleep(update_interval)
                response = self.get_progress_json()
                self.clear_counter()
                await ws.send_text(response)
        except (WebSocketDisconnect, ConnectionClosed):
            pass
        finally:
            try:
                await ws.send_text(self.get_progress_json())
            except (WebSocketDisconnect, ConnectionClosed):
                pass
            self.done.set()

    async def replay_stream(self, rec_id, prefix, name, fullspeed):
        def _unzip(data):
            import io
            import zipfile
            archive = io.BytesIO(data)
            with zipfile.ZipFile(archive, 'r', zipfile.ZIP_STORED, False) as zf:
                for ts in sorted(zf.namelist()):
                    with zf.open(ts, 'r') as f:
                        data = f.read()
                        yield ts, data

        sid = f'{prefix}{name}'
        fs = sorted(fglob(RECORDING_RAW_PATH, rec_id, name, '*'))

        firsts, lasts = tuple(zip(*(
            os.path.splitext(os.path.basename(f))[0].split('_')
            for f in fs
        ))) or ((),())
        first = parse_epoch_ts(min((t for t in firsts or () if t), default='0-0'))
        last = parse_epoch_ts(max((t for t in lasts or () if t), default='0-0'))
        self.durations[name] = last-first
        last = None
        try:
            for fname in fs:
                with open(fname, 'rb') as f:
                    for ts, data in _unzip(f.read()):
                        t = parse_epoch_ts(ts)
                        self.t_current[name] = t-first
                        timeout = 0
                        if not fullspeed:
                            now = (t, time.time())
                            last = last or now
                            timeout = max(timeout, (now[0]-last[0]) - (now[1]-last[1]))
                        with contextlib.suppress(asyncio.TimeoutError):
                            await asyncio.wait_for(self.done.wait(), timeout)
                        if self.is_done():
                            return
                        last = (t, time.time())
                        await Streams.add_entries(((sid, format_epoch_ts(last[1], '*'), data),))
                        self.update_counter(name)
        finally:
            self.set_inactive(name)

    async def replay(self, ws, rec_id, prefix, sids, fullspeed, update_interval=1):
        self.active = set(sids)
        await asyncio.gather(self.replay_progress(ws, update_interval),
                             *(self.replay_stream(rec_id, prefix, name, fullspeed)
                               for name in self.active))

# class Recordings:
#     def __init__(self) -> None:
#         pass

#     def list(self, stream_id):
#         return sorted((
#             os.path.basename(f)
#             for f in glob.glob(os.path.join(self.path, stream_id, f'**/*{self.EXT or ""}'))
#         ))

#     async def stream(self, name):
#         pass


# def _unzip(archive, name_only=False):
#     with zipfile.ZipFile(archive, 'r', zipfile.ZIP_STORED, False) as zf:
#         for ts in sorted(zf.namelist()):
#             if name_only:
#                 yield ts
#                 continue
            
#             with zf.open(ts, 'r') as f:
#                 data = f.read()
#                 yield ts, data
