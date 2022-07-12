import os
import glob
import datetime
from app.core.utils import parse_epoch_ts, parse_ts
from app.context import Context

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
            )))
        }

    def get_stream_info(self, rec_id, name):
        fs = fglob(RECORDING_RAW_PATH, rec_id, name, '*')
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

    def create_recording_id(self):
        #return f"rec-at-{str(int(time.time()))}"
        return datetime.datetime.now().strftime("%c")

    async def start(self, rec_id=None):
        rec_id = rec_id or self.create_recording_id()
        await ctx.redis.set(self.recording_id_key, rec_id)
        return rec_id

    async def stop(self):
        return await ctx.redis.delete(self.recording_id_key)


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
