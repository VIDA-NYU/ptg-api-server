import os
import glob
import zipfile


# class Recordings:
#     def __init__(self) -> None:
#         pass

#     def list(self, stream_id):
#         return sorted((
#             os.path.basename(f)
#             for f in glob.glob(os.path.join(self.path, stream_id, f'**/*{self.EXT or ""}'))
#         ))

#     async def stream(self, name):
#         pass


# def _unzip(archive, name_only=False):
#     with zipfile.ZipFile(archive, 'r', zipfile.ZIP_STORED, False) as zf:
#         for ts in sorted(zf.namelist()):
#             if name_only:
#                 yield ts
#                 continue
            
#             with zf.open(ts, 'r') as f:
#                 data = f.read()
#                 yield ts, data