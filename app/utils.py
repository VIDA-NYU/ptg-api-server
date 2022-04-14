import datetime
import orjson

def get_tag_names(tags):
    return list(map(lambda x: x['name'], tags))

def pack_entries(entries):
    offsets = []
    content = bytearray()
    for e in entries:
        offsets.append((e[0].decode('utf-8'),len(content)))
        content += e[1][b'd']
    jsonOffsets = orjson.dumps(offsets).decode('utf-8')
    return jsonOffsets, content

def redis_id_to_iso(rid):
    return datetime.datetime.fromtimestamp(int(rid.split(b'-')[0])/1000).isoformat(sep=' ')
