from typing import Optional
import datetime
import orjson
import pydantic


# def prints_traceback(func):
#     @functools.wraps(func)
#     def inner(*a, **kw):
#         try:
#             return func(*a, **kw)
#         except BaseException:
#             import traceback
#             traceback.print_exc()
#             raise
#     return inner


# def parse_stream_id(stream_id):
#     '''Parse the stream ID to get the device ID and the data type.
    
#     Examples:
    
#      - hololens1:depthahat
#      - hololens1:depthahat:1  # allow multiple streams under the same data type? idk - other option is to use glob for data converters
#     '''
#     if ':' not in stream_id:
#         return 'default', stream_id
#     device_id, dtype = stream_id.split(':', 1)
#     return device_id, dtype

def get_tag_names(tags):
    return [x['name'] for x in tags]

def pack_entries(entries):
    offsets = []
    content = bytearray()
    for sid, data in entries:
        sid = sid.decode('utf-8') if isinstance(sid, bytes) else sid
        for ts, d in data:
            offsets.append((sid, ts.decode('utf-8'), len(content)))
            content += d[b'd']
    jsonOffsets = orjson.dumps(offsets).decode('utf-8')
    return jsonOffsets, content



class DataModel(pydantic.BaseModel):
    class Config:
        arbitrary_types_allowed = True
    def __init__(self, *a, **kw):
        super().__init__(**dict(zip(self.__fields__, a)), **kw)


class AllOptional(pydantic.main.ModelMetaclass):
    def __new__(self, name, bases, namespaces, **kwargs):
        annotations = namespaces.get('__annotations__', {})
        for base in bases:
            annotations.update(base.__annotations__)
        for field in annotations:
            if not field.startswith('__'):
                annotations[field] = Optional[annotations[field]]
        namespaces['__annotations__'] = annotations
        return super().__new__(self, name, bases, namespaces, **kwargs)
