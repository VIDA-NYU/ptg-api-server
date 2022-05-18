'''Universal parser for Hololens messages.

'''
from collections import namedtuple
import cv2
from PIL import Image
import numpy as np
from .utils import DataModel

SensorTypeCls = namedtuple(
    'SensorType', 'PV DepthLT DepthAHAT GLL GLF GRF GRR Accel Gyro Mag numSensor Calibration')
SensorType = SensorTypeCls(*range(len(SensorTypeCls._fields)))

SensorStreamMap = {
    SensorType.PV: 'camera',
    SensorType.DepthLT: 'depthlt',
    SensorType.DepthAHAT: 'depthahat',
    SensorType.GLL: 'camlr', 
    SensorType.GLF: 'camlf',
    SensorType.GRF: 'camrf',
    SensorType.GRR: 'camrr',
    SensorType.Accel: 'accel',
    SensorType.Gyro: 'gyro',
    SensorType.Mag: 'mag',
    # SensorType.numSensor: 'numsensor',
    SensorType.Calibration: 'calibration',
}


def load_streams(data):
    '''Parse any frame of data coming from the hololens.'''
    version, data = np_pop(data, np.uint8)
    ftype, data = np_pop(data, np.uint8)
    timestamp, data = np_pop(data, np.uint64)
    w, data = np_pop(data, np.uint32)
    h, data = np_pop(data, np.uint32)
    stride, data = np_pop(data, np.uint32)
    info_size, data = np_pop(data, np.uint32)

    im_size = w*h*stride

    if ftype in {SensorType.Accel, SensorType.Gyro, SensorType.Mag}:
        assert stride == 4  # just checking - np_size(np.float32)
        sensorData, data = np_pop(data, np.float32, (h, w), im_size)
        timestamps, data = np_pop(data, np.uint64, size=info_size)
        timestamps = (timestamps - timestamps[0]) // 100 + timestamp
        key = (
            'accel' if ftype == SensorType.Accel else 
             'gyro' if ftype == SensorType.Gyro else 'mag')
        yield f'{key}:time', timestamps
        yield key, sensorData

    if ftype in {SensorType.DepthLT, SensorType.DepthAHAT}:
        assert stride == 2  # just checking - np_size(np.uint16)
        depth, data = np_pop(data, np.dtype(np.uint16).newbyteorder('>'), (h, w), im_size)
        yield 'depth', depth
        if info_size >= im_size:
            info_size -= im_size
            ab, data = np_pop(data, np.uint16, (h, w), im_size)
            yield 'brightness', ab
        
        if info_size > 0:
            cam2world, data = np_pop(data, np.float32, (4,4))
            cam2world = cam2world.T
            yield 'cam2world', cam2world

    if ftype in {SensorType.PV, SensorType.GLF, SensorType.GRR, SensorType.GRF, SensorType.GLL}:
        im, data = split(data, im_size)
        im = np.array(Image.frombytes('L', (w, h), im))
        
        if ftype in {SensorType.PV}:
            im = cv2.cvtColor(im[:,:-8], cv2.COLOR_YUV2RGB_NV12)
        elif ftype in {SensorType.GLF, SensorType.GRR}:
            im = np.rot90(im, -1)
        elif ftype in {SensorType.GRF, SensorType.GLL}:
            im = np.rot90(im)
        cam_name = SensorStreamMap[ftype]
        yield cam_name, im

        if info_size > 0:
            rig2world, data = np_pop(data, np.float32, (4,4))
            rig2world = rig2world.T
            yield f'{cam_name}:rig2world', rig2world
            if ftype in {SensorType.PV}:
                focal, data = np_pop(data, np.float32, (2,))
                yield f'{cam_name}:focal', focal

    if ftype in {SensorType.Calibration}:
        assert stride == 4  # just checking
        lut, data = np_pop(data, np.float32, (-1,3), im_size)
        yield 'calibration', lut
        rig2world, data = np_pop(data, np.float32, (4,4))
        rig2world = rig2world.T
        yield 'calibration:rig2world', rig2world

    raise ValueError(f"unknown frame type: {ftype}")







class SensorData(DataModel):
    frame_type: int
    accel: np.ndarray
    gyro: np.ndarray
    mag: np.ndarray
    timestamps: np.ndarray

    image: np.ndarray
    depth: np.ndarray
    ab_image: np.ndarray
    lut: np.ndarray

    cam2world: np.ndarray
    rig2world: np.ndarray
    focal: np.ndarray

    


def load(data):
    '''Parse any frame of data coming from the hololens.'''
    version, data = np_pop(data, np.uint8)
    ftype, data = np_pop(data, np.uint8)
    timestamp, data = np_pop(data, np.uint64)
    w, data = np_pop(data, np.uint32)
    h, data = np_pop(data, np.uint32)
    stride, data = np_pop(data, np.uint32)
    info_size, data = np_pop(data, np.uint32)

    im_size = w*h*stride

    if ftype in {SensorType.Accel, SensorType.Gyro, SensorType.Mag}:
        assert stride == 4  # just checking - np_size(np.float32)
        sensorData, data = np_pop(data, np.float32, (h, w), im_size)
        timestamps, data = np_pop(data, np.uint64, size=info_size)
        timestamps = (timestamps - timestamps[0]) // 100 + timestamp
        return SensorData(
            frame_type=ftype,
            accel=sensorData if ftype == SensorType.Accel else None,
            gyro=sensorData if ftype == SensorType.Gyro else None,
            mag=sensorData if ftype == SensorType.Mag else None,
            timestamps=timestamps)

    if ftype in {SensorType.DepthLT, SensorType.DepthAHAT}:
        assert stride == 2  # just checking - np_size(np.uint16)
        depth, data = np_pop(data, np.dtype(np.uint16).newbyteorder('>'), (h, w), im_size)
        if info_size >= im_size:
            info_size -= im_size
            ab, data = np_pop(data, np.uint16, (h, w), im_size)
        
        if info_size > 0:
            cam2world, data = np_pop(data, np.float32, (4,4))
            cam2world = cam2world.T
        return SensorData(frame_type=ftype, depth=depth, ab_image=ab)

    if ftype in {SensorType.PV, SensorType.GLF, SensorType.GRR, SensorType.GRF, SensorType.GLL}:
        im, data = split(data, im_size)
        im = np.array(Image.frombytes('L', (w, h), im))
        
        if ftype in {SensorType.PV}:
            im = cv2.cvtColor(im[:,:-8], cv2.COLOR_YUV2RGB_NV12)
        elif ftype in {SensorType.GLF, SensorType.GRR}:
            im = np.rot90(im, -1)
        elif ftype in {SensorType.GRF, SensorType.GLL}:
            im = np.rot90(im)
            
        if info_size > 0:
            rig2world, data = np_pop(data, np.float32, (4,4))
            rig2world = rig2world.T
            if ftype in {SensorType.PV}:
                focal, data = np_pop(data, np.float32, (2,))

        return SensorData(frame_type=ftype, image=im, rig2world=rig2world, focal=focal)

    if ftype in {SensorType.Calibration}:
        assert stride == 4  # just checking
        lut, data = np_pop(data, np.float32, (-1,3), im_size)
        rig2world, data = np_pop(data, np.float32, (4,4))
        rig2world = rig2world.T
        return SensorData(frame_type=ftype, lut=lut, rig2world=rig2world)

    raise ValueError(f"unknown frame type: {ftype}")



def np_read(data: bytes, dtype, shape=None):
    '''Reads a numpy array of type and shape from the start of a byte array.'''
    x = np.frombuffer(data, dtype)
    return x.reshape(shape) if shape else x.item()

def split(data, l):
    '''split an array at an index.'''
    return data[:l], data[l:]

def np_size(dtype, shape=None):
    '''Get the size of an array with data type and shape.'''
    if shape:
        for s in shape:
            if s < 0:
                raise ValueError("Can't get absolute size for a flexible shape array.")
            mult *= s
    return np.dtype(dtype).itemsize * mult

def np_pop(data, dtype, shape=None, size=None):
    '''Read a numpy array from a byte array and chop them from the start of the array.'''
    x, leftover = split(data, size or np_size(dtype, shape))
    return np_read(x, dtype, shape), leftover
