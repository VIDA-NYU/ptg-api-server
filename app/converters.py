'''Various methods of parsing formatting data from streams.

Basically, these are utilities to convert redis data (e.g. images) into 
usable data.

This was originally designed for parsing data from the hololens into jpeg/numpy, 
but maybe we'll just use the generic parser in holoframe instead.
'''
import io
import orjson
import numpy as np
from PIL import Image as pil
import cv2

from app.utils import Registry, DataModel, parse_stream_id

registry = Registry()


def get_converter(output_format=None, input_format=None, sid=None):
    '''Convert from one format to another. If a stream id (sid) is provided,
    check if we have a data formatter matching the data type name from the sid.
    '''
    formatter = lambda x: x
    if output_format:
        input_format = input_format or (parse_stream_id(sid)[1] if sid else None)
        load = registry[input_format]().load
        dump = registry[output_format]().dump
        formatter = lambda x: dump(load(x))
    return formatter


@registry.register
class Ndarray(DataModel):
    '''Convert numpy arrays to and from bytes.'''
    dtype: str = 'f'

    def load(self, data: bytes) -> np.ndarray:
        return np.frombuffer(data, dtype=self.dtype)

    def dump(self, data: np.ndarray) -> bytes:
        return np.asarray(data, dtype=self.dtype).tobytes()


@registry.register
class Json(DataModel):
    '''Convert json objects to and from bytes.'''
    def load(self, data: bytes) -> np.ndarray:
        return orjson.loads(data)

    def dump(self, data: np.ndarray) -> bytes:
        return orjson.dumps(data, option=orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_UTC_Z)


@registry.register
class Image(DataModel):
    '''Convert images to and from bytes.'''
    format: str = 'L'
    rotate: int = 0

    def load(self, data: bytes, width: int, height: int) -> np.ndarray:
        im = np.array(pil.frombytes(self.format, (width, height), data))
        if self.rotate:
            im = np.rot90(im, self.rotate)
        return im

    def dump(self, im: np.ndarray):
        if self.rotate:
            im = np.rot90(im, -self.rotate)
        return pil.fromarray(im).tobytes('raw', self.format, 0, 1)


@registry.register
class CompressedImage(DataModel):
    '''Convert images to and from bytes.'''
    format: str = 'jpg'

    def load(self, data: bytes, width: int, height: int) -> np.ndarray:
        im = np.array(pil.frombytes(self.format, (width, height), data))
        if self.rotate:
            im = np.rot90(im, self.rotate)
        return im

    def dump(self, im: np.ndarray):
        output = io.BytesIO()
        pil.fromarray(im).save(output, format=self.format)
        return output.getvalue()


@registry.register
class NV12(Image):
    '''Convert NV12 encoded images to and from bytes.'''
    def load(self, data: bytes, *a, **kw) -> np.ndarray:
        im = super().load(data, *a, **kw)
        im = cv2.cvtColor(im[:,:-8], cv2.COLOR_YUV2RGB_NV12)
        return im

    def dump(self, im: np.ndarray):
        return super().dump(bgr2nv12(im))


# register data formats
registry.variant('nv12', 'pv')
registry.variant('image', 'gll', rotate=1)
registry.variant('image', 'grf', rotate=1)
registry.variant('image', 'glf', rotate=-1)
registry.variant('image', 'grr', rotate=-1)
registry.variant('image', 'depthlt')
registry.variant('image', 'depthahat')
registry.variant('ndarray', 'accel')
registry.variant('ndarray', 'gyro')
registry.variant('ndarray', 'mag')
# formats to convert to
registry.variant('compressedimage', 'jpg', format='jpeg')
registry.variant('compressedimage', 'png', format='png')



def bgr2nv12(im: np.ndarray) -> np.ndarray:
    '''Helper to convert bgr images to nv12'''
    im = cv2.cvtColor(im, cv2.COLOR_BGR2YUV_I420)
    output = np.copy(im)
    uvi = im.shape[0] // 3 * 2
    uvh = im.shape[0] // 3 // 2
    w2 = im.shape[1] // 2
    output[uvi::2,    ::2] = im[uvi    :uvi + uvh,   :w2]
    output[uvi+1::2,  ::2] = im[uvi    :uvi + uvh,   w2:]
    output[uvi::2,   1::2] = im[uvi+uvh:uvi + uvh*2, :w2]
    output[uvi+1::2, 1::2] = im[uvi+uvh:uvi + uvh*2, w2:]
    return output



class HeaderFormat:
    '''Parses or dumps a specific header format.
    '''
    def __init__(self, formats: tuple | list):
        self.formats = formats
        self.sizes = [self._get_size(*f[1:]) for f in self.formats]
        self.offsets = np.cumsum(self.sizes) - self.sizes[0]
        self.size = sum(self.sizes)

    def _get_size(self, dtype: np.dtype | str, shape: tuple | list | None=None) -> int:
        mult = 1
        if shape:
            for s in shape:
                mult *= s
        return np.dtype(dtype).itemsize * mult

    def _parse_value(self, data: bytes, dtype, shape=None):
        x = np.frombuffer(data, dtype)
        return x.reshape(shape) if shape else x.item()

    def _dump_value(self, header, name, dtype, shape=None):
        return dtype(header.get(name, 0)).tobytes()

    def load(self, data: bytes) -> dict:
        return {
            fmt[0]: self._parse_value(data[start:start+size], *fmt[1:])
            for fmt, size, start in 
            zip(self.formats, self.sizes, self.offsets)
        }

    def dump(self, header: dict) -> bytes:
        return sum((self._dump_value(header, *f) for f in self.formats), b'')

    def pop(self, data: bytes):
        return self.load(data), data[self.size:]
    
    def unpack(self, header):
        return [header[f[0]] for f in self.formats]

# header_registry = Registry()

stream_header = HeaderFormat([
    ('VersionMajor', np.uint8),
    ('FrameType', np.uint8),
    ('timestamp', np.uint64),
    ('width', np.uint32),
    ('height', np.uint32),
    ('PixelStride', np.uint32),
    ('ExtraInfoSize', np.uint32),
])
# header_registry.register('nv12')(nv12_header)
