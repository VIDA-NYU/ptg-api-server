import orjson
from collections import defaultdict
from typing import Awaitable
from app.context import Context

ctx = Context.instance()

PROCEDURES = {
    'orange': [
        {'action':'grab an orange','label':'orange','delay':5},
        {'action':'slice the orange','label':'knife','delay':5},
        {'action':'squeeze in a wine glass','label':'wine glass','delay':5},
        {'action':'enjoy','label':'person','delay':5},
    ] ,
    'desk-stuff': [
        {'action':'grab a cup','label':'cup','delay':3},
        {'action':'grab an apple','label':'apple','delay':3},
        {'action':'grab your phone','label':'cell phone','delay':5},
    ],
}

class Session:

    @staticmethod
    def getProcedureSteps(pid: str):
        return PROCEDURES.get(pid, [])

    @staticmethod
    async def getProcedureInfo(uid: str):
        pid, index = await ctx.redisClient.mget(
            f'{uid}:procedure:id', f'{uid}:procedure:index')
        pid = pid.decode('utf-8')
        index = int(index or '0')
        steps = PROCEDURES.get(pid, [])
        return pid, index, steps

    @staticmethod
    async def setProcedureIndex(uid: str, index: int):
        return await ctx.redisClient.set(f'{uid}:procedure:index', index)
    
    @staticmethod
    async def setProcedureInfo(uid: str, pid: int, index: int):
        return await ctx.redisClient.mset({
            f'{uid}:procedure:id': pid, f'{uid}:procedure:index': index})
