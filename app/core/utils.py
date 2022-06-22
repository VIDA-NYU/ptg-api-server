import datetime



def parse_ts(tid):
    '''Convert a redis timestamp to a datetime object.'''
    return datetime.datetime.fromtimestamp(parse_epoch_ts(tid))

def parse_epoch_ts(tid):
    '''Convert a redis timestamp to epoch seconds.'''
    return int(tid.split('-')[0])/1000

def format_ts(dt: datetime.datetime):
    '''Format a redis timestamp from a datetime object.'''
    return format_epoch_ts(dt.timestamp())

def format_epoch_ts(tid: float):
    '''Format a redis timestamp from epoch seconds.'''
    return f'{int(tid * 1000)}-0'

def redis_id_to_iso(rid):
    '''Convert a redis timestamp to a iso format.'''
    return parse_ts(rid).isoformat(sep=' ')
