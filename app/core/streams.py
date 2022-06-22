import asyncio
import orjson
from collections import defaultdict
from typing import Awaitable
from app.context import Context
from app.core.utils import redis_id_to_iso

ctx = Context.instance()


def _postprocess_stream_info(info, meta, sid):
    d = {'sid': sid}
    if isinstance(info, Exception):
        info = {'error': str(info)}
    d.update(info or {})

    if d.get('first-entry'):
        d['first-entry'] = ts = d['first-entry'][0]
        d['first-entry-time'] = redis_id_to_iso(ts)
    if d.get('last-entry'):
        d['last-entry'] = ts = d['last-entry'][0]
        d['last-entry-time'] = redis_id_to_iso(ts)

    d['meta'] = str(meta) if isinstance(info, Exception) else meta
    return d

class Streams:
    META_PREFIX = 'XMETA'
    MAXLEN = ctx.config['default_max_len']
    async def list_streams(self):
        return [x.decode('utf-8') async for x in ctx.redis.scan_iter(_type='stream')]

    async def list_stream_info(self, sids=None):
        if sids is None:
            sids = await self.list_streams()
        async with ctx.redis.pipeline() as pipe:
            for sid in sids:
                pipe.get(f'{self.META_PREFIX}:{sid}').xinfo_stream(sid)
            res = await pipe.execute(raise_on_error=False)
            info = [
                _postprocess_stream_info(info, meta, sid)
                for sid, meta, info in zip(sids, res[::2], res[1::2])
            ]
        return info

    async def get_stream_info(self, sid):
        return (await self.list_stream_info([sid]))[0]

    async def get_stream_meta(self, sid):
        return await ctx.redis.get(f'{self.META_PREFIX}:{sid}')

    async def set_stream_meta(self, sid: str, *, _update=False, **meta):
        key = f'{self.META_PREFIX}:{sid}'
        if _update:
            previous = await ctx.redis.get(key)
            if previous:
                meta = dict(orjson.loads(previous), **meta)
        return await ctx.redis.set(key, orjson.dumps(meta))

    async def trim_stream(self, sid, maxlen=None, minid=None, **kw):
        return await ctx.redis.xtrim(sid, maxlen=maxlen, minid=minid, **kw)

    async def delete_stream(self, sid):
        async with ctx.redis.pipeline() as pipe:
            pipe.delete(f'{self.META_PREFIX}:{sid}')
            pipe.xtrim(sid, 0, approximate=False)
            return await pipe.execute()

    @staticmethod
    async def add_entries(entries: list):
        maxlen = ctx.config['default_max_len']
        async with ctx.redis.pipeline() as pipe:
            for sid, ts, data in entries:
                pipe.xadd(sid, {b'd': data}, ts or '*', maxlen=maxlen, approximate=True)
            res = await pipe.execute()
        return res

    @staticmethod
    async def get_entries(streams, count: int, block: int = None):
        star = [k for k, v in streams.items() if v == '*']
        nonstar = {k: v for k, v in streams.items() if v != '*'}

        async with ctx.redis.pipeline() as pipe:
            calls = [None, None]
            if star:
                for sid in star:
                    pipe.xrevrange(sid, count=count)
                calls[0] = pipe.execute()
            if nonstar:
                calls[1] = ctx.redis.xread(nonstar, count=count, block=block)
            res_star, res_nonstar = await asyncio.gather(*(x or noop() for x in calls))

        entries = [(sid, sorted(d)) for sid, d in zip(star, res_star)] + res_nonstar
        return entries

async def noop():
    return []
