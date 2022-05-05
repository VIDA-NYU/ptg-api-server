'''Where we can deploy ML tasks for the server.'''
import asyncio
from celery.task import task
from celery.contrib.abortable import AbortableTask
from app.context import Context
import app.models as models
import app.converters as converters
from app import holoframe
from app.workers.app import app
from app.store import DataStream


ctx = Context.instance()


@app.task(bind=True, base=AbortableTask)
def bounding_boxes(task, src_id, **kw):
    return asyncio.run(bounding_boxes_async(task, src_id, **kw))

# @app.task(bind=True, base=AbortableTask)
# def model_on_data_stream(task, model_name, src_id, dest_id, **kw):
#     return asyncio.run(model_on_data_stream_async(task, model_name, src_id, dest_id, **kw))


def parse_data(data):
    return holoframe.load(data).image

async def bounding_boxes_async(task, src_id, batch_size=4, model_name='yolov3', block=10000, last='$'):
    redis = ctx.redis
    assert await redis.ping()
    model = models.get(model_name)
    # device_id, data_type = src_id.split(':', 1)
    # parse_data = converters.registry.get('jpeg').load
    

    while not task.is_aborted():
        streams = await redis.xread(
            streams={src_id: last}, 
            count=batch_size, block=block)
        if not streams:
            continue

        # [[stream_name, [[ts, data], ...]], ...]
        ts, data = streams[0][1]
        data = parse_data(data)
        outputs = model(data)

        res = await DataStream.addEntries(f'{src_id}:{model_name}:boxes', [outputs])



# async def model_on_data_stream_async(task, model_name, src_id, dest_id, batch_size=4, block=10000, last='$'):
#     redis = ctx.redis
#     assert await redis.ping()
#     model = models.get(model_name)
#     device_id, data_type = src_id.split(':', 1)

#     parse_data = converters.registry.get(data_type).load

#     while not task.is_aborted():
#         streams = await redis.xread(
#             streams={src_id: last}, 
#             count=batch_size, block=block)
#         if not streams:
#             continue

#         # [[stream_name, [[ts, data], ...]], ...]
#         ts, data = streams[0][1]
#         data = parse_data(data)
#         outputs = model(data)

#         await redis.xadd(dest_id, )
#         # _id = await red.xadd(f'{uid}:{name}', { 'index': i, field: data }, maxlen=maxlen)
