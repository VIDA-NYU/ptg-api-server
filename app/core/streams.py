import time
import asyncio
import orjson
from collections import defaultdict
from typing import Awaitable
from app.context import Context
from app.core.utils import redis_id_to_iso,  parse_epoch_time, format_epoch_ts

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
        return sorted([x.decode('utf-8') async for x in ctx.redis.scan_iter(_type='stream')])

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
            for sid in sid.split('+'):
                pipe.delete(f'{self.META_PREFIX}:{sid}')
                pipe.xtrim(sid, 0, approximate=False)
                pipe.delete(sid)
            return await pipe.execute()

    @staticmethod
    async def add_entries(entries: list, include_static_key=False):
        maxlen = ctx.config['default_max_len']
        async with ctx.redis.pipeline() as pipe:
            for sid, ts, data in entries:
                pipe.xadd(sid, {b'd': data}, ts or '*', maxlen=maxlen, approximate=True)
                if include_static_key:
                    pipe.set(sid, data)
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
            #print('block', block, [[s, len(t)] for s,t in res_nonstar])

        entries = [(sid, sorted(d)) for sid, d in zip(star, res_star)] + res_nonstar
        return entries

async def noop():
    return []



def maybe_utf_encode(txt):
    return txt.encode('utf-8') if isinstance(txt, str) else txt

def maybe_utf_decode(txt):
    return txt.decode('utf-8') if isinstance(txt, bytes) else txt

class MultiStreamCursor:
    def __init__(self, last, latest=True, block=10000, time_sync_id=None, replace_dollar=True, redis=None):
        self.r = ctx.redis if redis is None else redis
        tnow = format_epoch_ts(time.time())
        self.last = {
            maybe_utf_encode(sid): tnow if replace_dollar and t == '$' else t
            for sid, t in last.items()
        }
        self.latest = latest
        self.block = block
        self.time_sync_id = maybe_utf_encode(time_sync_id)

    async def next(self, **kw):
        # query next value
        result = await (self.next_latest(**kw) if self.latest else self.next_consecutive(**kw))
        # update to the latest timestamp
        for sid, ts in result:
            self.last[sid] = max((t for t, _ in ts), default=self.last[sid])
        if self.time_sync_id:
            main_ts = self.last[self.time_sync_id]
            for sid in self.last:
                self.last[sid] = main_ts
        return result

    async def next_latest(self, **kw):
        '''Query the latest new frame.

        Not all streams are guaranteed to return a value.

        1 <= len(streams) <= len(stream_id_query)

        Scenarios:
         - there is new data in all streams
            - returned: the latest new value value for each stream
         - there is no new data in any stream
            - initial revrange queries all return empty
            - block until one of the streams returns a value
            - XXX: we could run revrange again if we are still missing streams?
         - there is some new data in the streams
            - returned: the streams with new data
        '''
        result = await self._next_latest(**kw)
        if result:
            return result
        result = await self.next_consecutive(**kw)
        return result

    async def _next_latest(self, sids=None, count=1):
        sids = sids or self.last
        # xrevrange, don't include last queried value
        start_time = time.time()
        async with self.r.pipeline() as p:
            for s in sids:
                l = maybe_utf_decode(self.last[s])
                if l == '$':
                    self.last[s] = l = format_epoch_time(start_time)
                p.xrevrange(s, '+', f'({l}' if l != '-' else '-', count=count)
            return [(s, x) for s, x in zip(sids, await p.execute()) if x]
            # if we use $, filter out any timestamps before the start time (since xrevrange doesn't actually support $)
            # also filter out empty stream IDs
            #return [
            #    (s, r) for s, r in (
            #        (s, [(ts, x) for ts, x in r if parse_epoch_time(ts) > start_time] if self.last[s] == '$' else r) 
            #        for s, r in zip(sids, await p.execute()) 
            #    ) if r
            #]


    async def next_consecutive(self, count=1):
        '''Query the next consecutive frame.

        Will return whatever is available. Will only block if no streams
        are
        '''
        # block using last timestamp
        return await self.r.xread(self.last, block=self.block, count=count)

