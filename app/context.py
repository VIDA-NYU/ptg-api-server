from collections import defaultdict
from functools import cache
import aioredis
import asyncio
import json
import os
import starlette.datastructures

class Context:

    @staticmethod
    @cache
    def instance():
        return Context()

    def __init__(self, configFile: str|None=None):
        self.redis = None
        self.redisClient = None # Redis connection for client-side support

        self.path = os.path.dirname(__file__)
        if not configFile:
            configFile = os.path.join(self.path, 'config.json')
        assert os.path.exists(configFile)
        self.config = defaultdict(lambda x: None, json.load(open(configFile, 'r')))
        starlette.datastructures.UploadFile.spool_max_size = int(self.config.get('spool_max_size', 0))

    def getDescription(self):
        readme = os.path.join(self.path, '..', 'README.md')
        desc = (open(readme, 'r').read()
                if os.path.exists(readme)
                else self.config['description'])
        return desc.split('## Setup Instructions')[0].split('# PTG Data Store API\n')[-1]

    async def initialize(self):
        connection = self.config['redis']['connection']
        self.redis = await aioredis.from_url(**connection)
        self.redisClient = await aioredis.from_url(**connection, db=1)
        await asyncio.gather(self.redis.ping(),self.redisClient.ping())

