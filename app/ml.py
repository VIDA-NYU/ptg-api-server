'''Where we can deploy ML tasks for the server.

TODO: convert this to a celery task ????

other models:
 - video clsf: 
    - https://pytorch.org/hub/facebookresearch_pytorchvideo_resnet/
    - https://pytorch.org/hub/facebookresearch_pytorchvideo_x3d/
    - https://pytorch.org/hub/facebookresearch_pytorchvideo_slowfast/
    - https://pytorch.org/hub/pytorch_vision_fcn_resnet101/
 - spoof depth images: https://pytorch.org/hub/intelisl_midas_v2/

'''
import asyncio
import orjson

import numpy as np
from PIL import Image
import torch

from app.context import Context
import app.converters as converters
from app import holoframe


ctx = Context.instance()


def yolo5(src_id, **kw):
    return asyncio.run(yolo5_async(src_id, **kw))

cols = ['x', 'y', 'w', 'h', 'confidence', 'label'] #
async def yolo5_async(src_id, *a, **kw):
    dest_id = f'{src_id}:boxes'
    model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
    async for im in report_fps(reader(src_id, *a, **kw)):
        h, w = im.shape[:2]
        dets = model(im)
        xywh = dets.xywhn[0]
        xywh[:,:2] -= xywh[:,2:4] / 2
        # xywh = xywh / np.array([w,h,w,h,1,1])
        outputs = [
            dict(zip(cols, x), label=dets.names[int(x[-1])]) 
            for x in xywh.tolist()
        ]
        print(dest_id, outputs)
        # res = await DataStream.addEntries(f'{src_id}:boxes', [outputs])
        r = await ctx.redis.xadd(dest_id, {b'd': orjson.dumps(outputs)}, approximate=True)
        print(r)


# def deeplabv3(src_id, **kw):
#     return asyncio.run(deeplabv3_async(src_id, **kw))

# async def deeplabv3_async(*a, **kw):
#     from torchvision import transforms
#     model = torch.hub.load('pytorch/vision:v0.10.0', 'deeplabv3_resnet50', pretrained=True)
#     model.eval()

#     preprocess = transforms.Compose([
#         transforms.ToTensor(),
#         transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
#     ])
#     # create a color pallette, selecting a color for each class
#     palette = torch.tensor([2 ** 25 - 1, 2 ** 15 - 1, 2 ** 21 - 1])
#     colors = torch.as_tensor([i for i in range(21)])[:, None] * palette
#     colors = (colors % 255).numpy().astype("uint8")

#     async for ims in reader(*a, **kw):
#         im = ims[-1]
#         im = preprocess(im)[0]
#         with torch.no_grad():
#             output = model(im)['out'][0]
#         output = output.argmax(0)

#         # plot the semantic segmentation predictions of 21 classes in each color
#         r = Image.fromarray(output.byte().cpu().numpy())#.resize(im.size)
#         r.putpalette(colors)

#         # res = await DataStream.addEntries(f'{src_id}:boxes', [outputs])



async def reader(src_id, batch_size=1, is_jpg=False, block=10000, last='-', no_data_sleep=2):
    if ctx.redis is None:
        await ctx.initialize()
    redis = ctx.redis
    assert await redis.ping()

    parse_jpg = converters.registry['jpg']().load
    def parse_holo_im(data):
        return holoframe.load(data).image
    parse = parse_jpg if is_jpg else parse_holo_im

    while True:
        streams = await redis.xrevrange(src_id, count=batch_size, min=last)#f'{last})' if last else '-'
        if not streams or streams[-1][0] == last:
            print('no data', flush=True)
            await asyncio.sleep(no_data_sleep)
            continue
        last, data = streams[-1]
        yield parse(data[b'd'])


async def report_fps(it, display=10, i=0):
    import time
    start_time = time.time()
    fps = 0
    async for x in it:
        yield x
        i += 1
        dt = time.time() - start_time
        fps = i / dt
        if dt > display:
            print("FPS: ", fps)
            i = 0
            start_time = time.time()

if __name__ == '__main__':
    import fire
    fire.Fire()