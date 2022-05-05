import functools
import datetime
import orjson
import pydantic


def parse_stream_id(stream_id):
    '''Parse the stream ID to get the device ID and the data type.
    
    Examples:
    
     - hololens1:depthahat
     - hololens1:depthahat:1  # allow multiple streams under the same data type? idk - other option is to use glob for data converters
    '''
    if ':' not in stream_id:
        return 'default', stream_id
    device_id, dtype = stream_id.split(':', 1)
    return device_id, dtype

def get_tag_names(tags):
    return list(map(lambda x: x['name'], tags))

def unzip_entries(entries):
    offsets = []
    content = bytearray()
    for sid,data in entries:
        sid = sid.decode('utf-8') if isinstance(sid, bytes) else sid
        for d in data:
            offsets.append((sid,d[0].decode('utf-8'),len(content)))
            content += d[1][b'd']
    jsonOffsets = orjson.dumps(offsets).decode('utf-8')
    return jsonOffsets, content

def redis_id_to_iso(rid):
    return datetime.datetime.fromtimestamp(int(rid.split(b'-')[0])/1000).isoformat(sep=' ')


class DataModel(pydantic.BaseModel):
    def __init__(self, *a, **kw):
        super().__init__(**dict(zip(self.__fields__, a)), **kw)



class Registry:
    '''This is a basic lookup table for functions and classes.
    You register them and then look them up by name later.
    This also supports lazy imports using ``register_module``.

    Register like this:

    .. code-block:: python

        registry = Registry()

        @registry.register
        def something():
            pass

        @registry.register('blah')
        def something_else():
            pass

        assert registry.get('something') is something
        assert registry.get('blah') is something_else
        registry.get('something_else')  # KeyError

    Lazy imports (in case there are big dependencies)

    .. code-block:: python

        @registry.register_module('torch_model')
        def import_something_big():
            import some_torch_model  # don't want to do this if you dont have to
            # can call register inside some_torch_model
            # from . import registry
            # @registry.register
            # class Myclass: ...
            
            # or if you prefer, register here
            registry.register(some_torch_model.Myclass)

    Then to make sure that the namespace imports, you'll have to prefix 
    the model name with the namespace.

    .. code-block:: python

        registry.get('torch_model/myclass')

        # if you know your class has already been imported and registered, 
        # you can just do
        registry.get('myclass')
    '''
    def __init__(self):
        # lazy imports
        self.modules = {}
        # object factories
        self.lookup = {}

    def __contains__(self, name):
        return name in self.lookup

    def register(self, name=None):
        return _register(self.lookup, name)

    def register_module(self, name=None):
        return _register(self.modules, name)

    def variant(self, base_name, name, *a, **kw):
        if not name:
            # make an id from the args
            arg_id = ",".join(
                tuple(map(str, a)) + 
                tuple(f"{k}={v!r}" for k, v in kw.items()))
            name = f'{name}{arg_id}'
        # create and register the function with partial args
        func = functools.partial(self.lookup[base_name.lower()], *a, **kw)
        func.__name__ = name
        return self.register(name)(func)

    def update(self, funcs):
        for k, v in funcs.items():
            self.register(k)(v)

    def merge(self, other_registry: 'Registry'):
        self.modules.update(other_registry.modules)
        self.lookup.update(other_registry.lookup)
        return self

    # def get(self, name, *a, **kw):
    #     return self[name](*a, **kw)

    def __getitem__(self, name):
        name = name.lower()
        mod, name = name.split('/', 1) if '/' in name else (None, name)

        # try lazy import
        if mod and name not in self.lookup:
            self.modules[mod]()
        # try model
        return self.lookup[name]

    def load(self, module):
        if module:
            self.modules[module.lower()]()
        return self


def _register(self, name=None):
    # work as a decorator
    def reg(func):
        key = (name or func.__name__).lower()
        self[key] = func
        return func
    # if the user didnt provide a name, just call the decorator on the provided function
    if callable(name):
        func, name = name, None
        return reg(func)
    # otherwise wait to be called again
    return reg
