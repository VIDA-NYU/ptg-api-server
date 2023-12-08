from __future__ import annotations
from collections import defaultdict
from functools import cache
import asyncio
import redis
from redis import asyncio as aioredis
import json
import os
import starlette.datastructures


def load_config(fname):
    with open(fname, 'r') as f:
        config = defaultdict(lambda: None, json.load(f))

    # set some defaults
    starlette.datastructures.UploadFile.spool_max_size = int(config.get('spool_max_size') or 0)
    return config

def get_desc(path):
    f = os.path.join(self.path, '..', 'README.md')
    desc = (open(f, 'r').read() if os.path.exists(f) else self.config['description'] or '')
    return desc.split('## Setup Instructions')[0].split('# PTG Data Store API\n')[-1]

class Context:
    path = os.path.dirname(__file__)

    @staticmethod
    @cache
    def instance():
        return Context()

    def __init__(self, configFile: str | None=None):
        # self.redis = None
        # self.redisClient = None # Redis connection for client-side support
        self.config = load_config(configFile or os.path.join(self.path, 'config.json'))

    def getDescription(self):
        f = os.path.join(self.path, '..', 'README.md')
        desc = (open(f, 'r').read() if os.path.exists(f) else self.config['description'] or '')
        return desc.split('## Setup Instructions')[0].split('# PTG Data Store API\n')[-1]

    initialized = False
    async def initialize(self):
        self.initialized = True
        connection = self.config['redis']['connection']
        url = os.getenv('REDIS_URL')
        if url:
            connection['url'] = url

        while True:
            try:
                self.redis = await aioredis.from_url(**connection)
                self.redisClient = await aioredis.from_url(**connection, db=1)
                await asyncio.gather(self.redis.ping(), self.redisClient.ping())
                break
            except redis.exceptions.ConnectionError as e:
                await asyncio.sleep(3)
                print("Error initializing connection to redis.")
                print(type(e).__name__, e)


class Context2:
    path = os.path.dirname(__file__)
    def __init__(self, config_fname):
        self._conns = {}
        self.config = load_config(config_fname or os.path.join(self.path, 'config.json'))

    async def redis(self, db=0):
        if db not in self._conns:
            await self._initialize(db=db)
        return self._conns[db]

    async def _initialize(self, db=0):
        connection = self.config['redis']['connection']
        url = os.getenv('REDIS_URL')
        if url:
            connection['url'] = url
        connection['db'] = db
        self._conns[db] = await aioredis.from_url(**connection)
        await self._conns[db].ping()

#ctx = Context2()

