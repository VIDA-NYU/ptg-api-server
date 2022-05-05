'''Meant to monitor streams and spawn/stop background tasks to process the streams.

'''
import asyncio
from app.store import DataStore
from celery.contrib.abortable import AbortableTask
from .app import app

async def schedule_async(task_name, sleep_for=1):
    while True:
        streams = DataStore.get().meta['streams']
        for s, info in streams.items():
            task_id = info[f'task_id:{task_name}']
            is_on = task_id and task_id is not True
            if task_id:
                if not is_on:
                    app.send_task(task_name, )
            else:
                if is_on:
                    
                    pass
        await asyncio.sleep(sleep_for)