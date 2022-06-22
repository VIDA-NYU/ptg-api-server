from __future__ import annotations
from collections import defaultdict
from functools import cache
import asyncio
from redis import asyncio as aioredis
import json
import os
import starlette.datastructures


def load_config(fname):
    fname = fname or os.path.join(Context.path, 'config.json')
    assert os.path.exists(fname)
    with open(fname, 'r') as f:
        config = defaultdict(lambda: None, json.load(f))

    # set some defaults
    starlette.datastructures.UploadFile.spool_max_size = int(config.get('spool_max_size') or 0)
    return config

class Context:
    path = os.path.dirname(__file__)

    @staticmethod
    @cache
    def instance():
        return Context()

    def __init__(self, configFile: str | None=None):
        # self.redis = None
        # self.redisClient = None # Redis connection for client-side support
        self.config = load_config(configFile)

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
        self.redis = await aioredis.from_url(**connection)
        self.redisClient = await aioredis.from_url(**connection, db=1)
        await asyncio.gather(self.redis.ping(), self.redisClient.ping())

