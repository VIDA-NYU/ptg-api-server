'''Recording data streams and writing them to disk.'''
import os
import io
import asyncio
# import contextlib
from app.context import Context
from app.workers.app import app
from celery.contrib.abortable import AbortableTask

ctx = Context.instance()


@app.task(bind=True, base=AbortableTask)
def store_streams(task, *stream_ids, **kw):
    asyncio.run(store_streams(task, *stream_ids, **kw))


async def store_data_stream(task, stream_id, use_gdrive=False):
    drive = GDrive() if use_gdrive else Disk()
    async for entries in reader(task, stream_id):
        if entries:
            drive.store_entries(entries, stream_id)


async def store_streams_async(task, *stream_ids, **kw):
    return await asyncio.gather(*(
        store_data_stream(task, sid, **kw) for sid in stream_ids))




class GDrive:
    def __init__(self):
        from googleapiclient.http import MediaIoBaseUpload
        from apiclient.discovery import build
        from oauth2client.service_account import ServiceAccountCredentials
        self.MediaUpload = MediaIoBaseUpload
        scopes = ["https://www.googleapis.com/auth/drive"]
        service = 'service_account.json'
        credentials = ServiceAccountCredentials.from_json_keyfile_name(service, scopes)
        self.dataFolder = '1b3C5NoFs_ErvfpS9wh9YNVaIFLj5o3yL'
        self.drive = build('drive', 'v3', credentials=credentials)

    def list(self):
        return self.drive.files().list().execute().get('files', [])

    def upload(self, fn, data, mimetype='application/octet-stream'):
        media = self.MediaUpload(
            io.BytesIO(data), mimetype=mimetype, 
            chunksize=1024*1024, resumable=True)
        return self.drive.files().create(
            body={'name': fn, 'parents': [self.dataFolder]}, 
            media_body=media, fields='id').execute()

    def store_entries(self, entries, stream_id=None):
        fn, archive = zip_entries(entries, stream_id)
        self.upload(fn, archive, mimetype='application/zip')


class Disk:
    def __init__(self, path='./data'):
        self.path = path
        os.makedirs(self.path, exist_ok=True)

    def store_entries(self, entries, stream_id=None):
        fn, archive = zip_entries(entries, stream_id)
        with open(os.path.join(self.directory, fn), 'wb') as f:
            f.write(archive)


async def reader(task, sid='dev0', max_size=9500000, max_len=1000, batch_size=1000, block=10000, last='$'):
    redis = ctx.redis
    assert(await redis.ping())

    while not task.is_aborted():
        size = 0
        entries = []
        while len(entries) <= max_len and size <= max_size:
            streams = await redis.xread(
                streams={sid: last}, 
                count=batch_size, block=block)
            if not streams:
                continue

            new_entries = streams[0][1]
            size += sum(len(x[1][b'd']) for x in new_entries)
            entries.extend(new_entries)
            last = entries[-1][0]
        yield entries


def zip_entries(entries, stream_id=None):
    import zipfile
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_STORED, False) as zf:
        for ts, data in entries:
            zf.writestr(ts.decode('utf-8'), data[b'd'])
    prefix = f'{stream_id}_' if stream_id else ''
    fn = f'{prefix}{entry2timestamp(entries[0])}_{entry2timestamp(entries[-1])}.zip'
    return fn, archive.getvalue()


def entry2timestamp(entry):
    return entry[0].decode('utf-8').split('-')[0]


if __name__ == '__main__':
    import fire
    fire.Fire(store_streams.run)