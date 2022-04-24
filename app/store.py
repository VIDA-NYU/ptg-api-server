import orjson
from collections import defaultdict
from typing import Awaitable
from app.context import Context

ctx = Context.instance()

class DataStore:

    @staticmethod
    def get() -> Awaitable:
        key = ctx.config['redis']['meta_key']
        store = DataStore(key)
        return store.load()

    @staticmethod
    async def getStreamInfo(sid: str):
        key = ctx.config['redis']['meta_key']
        async with ctx.redis.pipeline() as pipe:
            meta, info = await pipe.get(key) \
                                   .xinfo_stream(sid) \
                                   .execute(raise_on_error=False)
        meta = (str(meta) if isinstance(meta, Exception) else
                (orjson.loads(meta)['streams'].get(sid, {}) if meta else {}))
        info = str(info) if isinstance(info, Exception) else info
        return (meta, info)
    
    def __init__(self, redisKey: str):
        self.redisKey = redisKey
        self.meta = defaultdict(dict)

    async def load(self, value: str | None = None):
        if value==None:
            value = await ctx.redis.get(self.redisKey)
        if value:
            self.meta.update(orjson.loads(value))
        return self

    def save(self) -> Awaitable:
        value = orjson.dumps(self.meta)
        return ctx.redis.set(self.redisKey, value)

    async def getStreamIds(self):
        keys = await ctx.redis.keys()
        return list(filter(lambda x: x.decode('utf-8')!=self.redisKey, keys))

    def hasStreamId(self, sid: str) -> bool:
        return sid in self.meta['streams']

    def getStream(self, sid: str) -> dict:
        stream = self.meta['streams'][sid]
        stream['metadata'] = orjson.loads(stream.get('meta', '{}'))
        return stream

    def createStream(self, sid: str, desc: str|None=None, meta: str|None='{}',  max_len: int|None=None) -> Awaitable:
        self.meta['streams'][sid] = {
            'id': sid,
            'description': desc if desc!=None else sid,
            'metadata': meta,
            'max_len': max_len if max_len!=None else ctx.config['default_max_len']
        }
        return self.save()

    async def deleteStream(self, sid: str):
        stream = self.meta['streams'].pop(sid, None)
        if stream:
            await self.save()
        return stream

class DataStream:

    @staticmethod
    async def addEntries(entries: list):
        maxlen = ctx.config['default_max_len']
        async with ctx.redis.pipeline() as pipe:
            for (sid,data) in entries:
                pipe.xadd(sid, {b'd':data}, maxlen=maxlen, approximate=True)
            res = await pipe.execute()
        return res

    @staticmethod
    async def getEntries(streams, count: int, block: int = None):
        star = list(filter(lambda x: x[1]=='*', streams.items()))
        nonstar = dict(filter(lambda x: x[1]!='*', streams.items()))
        async with ctx.redis.pipeline() as pipe:
            for (sid,last) in star:
                pipe.xrevrange(sid, count=count)
            if nonstar:
                pipe.xread(streams=nonstar, count=count, block=block)
            res = await pipe.execute()
        entries = list(zip(map(lambda x: x[0], star), map(reversed, res)))
        if nonstar and res[-1]:
            entries += res[-1]
        return entries
