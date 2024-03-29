import asyncio
import orjson
import numpy as np
import ptgctl
import ptgctl.holoframe
from ptgctl.pt3d import Points3D

import warnings
warnings.filterwarnings('ignore', message="User provided device_type of 'cuda'")


class App:
    def __init__(self):
        self.api = ptgctl.CLI(local=False)
        self.load_model()
        self.calibrate()

    def load_model(self):
        import torch
        device_type = 'cuda' if torch.cuda.is_available() else 'cpu'
        device = torch.device(device_type)
        self.model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True).to(device)
        self.model.amp = False
        self.labels = np.asarray(self.model.names)

    def calibrate(self):
        data = ptgctl.holoframe.load_all(self.api.data('depthltCal'))
        self.lut, self.T_rig2cam = ptgctl.holoframe.unpack(data, [
            'depthltCal.lut', 
            'depthltCal.rig2cam', 
        ])

    def run(self, **kw):
        return asyncio.run(self.run_async(**kw))

    async def run_async(self, **kw):
        streams = ['main', 'depthlt']
        async with self.api.data_pull_connect('+'.join(streams), **kw) as wsr:
            # async with self.api.data_push_connect('+'.join(streams), **kw) as wsw:
                while True:
                    data = await wsr.recv_data()
                    if not data:
                        print('empty data')
                        await asyncio.sleep(0.1)
                        continue
                    data = ptgctl.holoframe.load_all(data)
                    ts = ptgctl.util.parse_time(data['main']['timestamp'])
                    print('timestamp difference:', {
                        k: str(ts - ptgctl.util.parse_time(d['timestamp']))
                        for k, d in data.items() if 'timestamp' in d
                    })

                    (
                        rgb, depth,
                        T_rig2world, T_pv2world, 
                        focalX, focalY, principalX, principalY,
                    ) = ptgctl.holoframe.unpack(
                        data, [
                        'main.image', 
                        'depthlt.image', 
                        'depthlt.rig2world', 
                        'main.cam2world', 
                        'main.focalX', 
                        'main.focalY', 
                        'main.principalX',
                        'main.principalY',
                    ])

                    pts3d = Points3D(
                        rgb, depth, self.lut, 
                        T_rig2world, self.T_rig2cam, T_pv2world, 
                        [focalX, focalY], 
                        [principalX, principalY])
                    results = self.process_data(rgb, pts3d)
                    output = orjson.dumps(self.as_json(results), option=orjson.OPT_NAIVE_UTC | orjson.OPT_SERIALIZE_NUMPY)
                    # wsw.send_data(output)
                    print(output)

    def process_data(self, rgb, pts3d):
        results = self.model(rgb)
        xyxy = results.xyxy[0].numpy()
        meta = xyxy[:, 4:]

        (
            xyz_tl_world, xyz_br_world, 
            xyz_tr_world, xyz_bl_world, 
            xyzc_world, dist,
        ) = pts3d.transform_box(xyxy[:, :4])
        valid = dist < 5  # make sure the points aren't too far

        print(xyxy.shape, xyz_tl_world.shape)
        print(valid.sum(), dist)
        print(xyzc_world)

        xs = [xyz_tl_world, xyz_br_world, xyz_tr_world, xyz_bl_world, xyzc_world, meta]
        xs = [x[valid] for x in xs]
        return np.concatenate(xs, axis=1)

    columns = [
        'x_tl', 'y_tl', 'z_tl', 
        'x_br', 'y_br', 'z_br', 
        'x_tr', 'y_tr', 'z_tr', 
        'x_bl', 'y_bl', 'z_bl', 
        'xc', 'yc', 'zc', 
        'confidence', 'class_id']
    def as_json(self, results):
        return [
            dict(zip(self.columns, d), label=self.labels[int(d[-1])])
            for d in results
        ]


if __name__ == '__main__':
    import fire
    fire.Fire(App)

