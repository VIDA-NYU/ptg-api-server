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


ctx = Context.instance()

fglob = lambda *fs: glob.glob(os.path.join(*fs))

class Recordings:
    recording_id_key='recording:id'
    def list_recordings(self):
        fs = fglob(RECORDING_RAW_PATH, '*')
        return [os.path.basename(f) for f in fs]

    def list_recording_info(self):
        return [self.get_recording_info(rid) for rid in self.list_recordings()]

    async def get_current_recording(self, info=False):
        rid = await ctx.redis.get(self.recording_id_key)
        rid = rid.decode('utf-8') if rid else rid
        if info:
            return self.get_recording_info(rid) if rid else None
        return rid

    def get_recording_info(self, rec_id):
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
            "files": os.listdir(os.path.join(RECORDING_POST_PATH, rec_id)),
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
        return {
            "duration": str(datetime.timedelta(seconds=parse_epoch_ts(last) - parse_epoch_ts(first))) if first and last else None,
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
        return rec_id

    async def stop(self):
        return await ctx.redis.delete(self.recording_id_key)

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

    def clear_counter(self):
        self.counter.clear()

    def update_counter(self, sid):
        self.counter[sid] += 1

    def get_progress_json(self):
        progress = {'updates': list(self.counter.items()), 'active': list(self.active)}
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
        last = None
        try:
            for fname in fs:
                with open(fname, 'rb') as f:
                    for ts, data in _unzip(f.read()):
                        t = parse_epoch_ts(ts)
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
                        await Streams.add_entries(((sid, format_epoch_ts(last[1]), data),))
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
