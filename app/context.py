from collections import defaultdict
from functools import cache
import aioredis
import json
import os

class Context:

    @staticmethod
    @cache
    def instance():
        return Context()

    def __init__(self, configFile: str|None=None):
        self.redis = None
        self.path = os.path.dirname(__file__)
        if not configFile:
            configFile = os.path.join(self.path, 'config.json')
        assert os.path.exists(configFile)
        self.config = defaultdict(lambda x: None, json.load(open(configFile, 'r')))

    def getDescription(self):
        readme = os.path.join(self.path, '..', 'README.md')
        desc = (open(readme, 'r').read()
                if os.path.exists(readme)
                else self.config['description'])
        return desc.split('## Setup Instructions')[0].split('# PTG Data Store API\n')[-1]

    async def initialize(self):
        connection = self.config['redis']['connection']
        self.redis = await aioredis.from_url(**connection)
        await self.redis.ping()
