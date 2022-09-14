import datetime



def parse_ts(tid):
    '''Convert a redis timestamp to a datetime object.'''
    return datetime.datetime.fromtimestamp(parse_epoch_ts(tid))

def parse_epoch_ts(tid):
    '''Convert a redis timestamp to epoch seconds.'''
    if isinstance(tid, bytes):
        tid = tid.decode('utf-8')
    return int(tid.split('-')[0])/1000

def format_ts(dt: datetime.datetime):
    '''Format a redis timestamp from a datetime object.'''
    return format_epoch_ts(dt.timestamp())

def format_epoch_ts(tid: float, i='0'):
    '''Format a redis timestamp from epoch seconds.'''
    return f'{int(tid * 1000)}-{i}'

def redis_id_to_iso(rid):
    '''Convert a redis timestamp to a iso format.'''
    return parse_ts(rid).isoformat(sep=' ')

parse_time = parse_ts
parse_epoch_time = parse_epoch_ts
format_time = format_ts
format_epoch_time = format_epoch_ts
