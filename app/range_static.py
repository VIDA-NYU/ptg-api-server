import os
import re
import stat
import typing as t
from urllib.parse import quote

import aiofiles
from aiofiles.os import stat as aio_stat
from starlette.datastructures import Headers
from starlette.exceptions import HTTPException
from starlette.responses import Response, guess_type
from starlette.staticfiles import StaticFiles
from starlette.types import Receive, Scope, Send


RANGE_REGEX = re.compile(r"^bytes=(?P<start>\d+)-(?P<end>\d*)$")


PathLike = t.Union[str, "os.PathLike[str]"]


class OpenRange(t.NamedTuple):
    start: int
    end: t.Optional[int] = None

    def clamp(self, start: int, end: int) -> "ClosedRange":
        begin = max(self.start, start)
        end = min((x for x in (self.end, end) if x))
        return ClosedRange(min(begin, end), max(begin, end))


class ClosedRange(t.NamedTuple):
    start: int
    end: int

    def __len__(self) -> int:
        return self.end - self.start + 1

    def __bool__(self) -> bool:
        return len(self) > 0


class RangedFileResponse(Response):
    chunk_size = 4096

    def __init__(
        self,
        path: PathLike,
        range: OpenRange,
        headers: t.Optional[t.Dict[str, str]] = None,
        media_type: t.Optional[str] = None,
        filename: t.Optional[str] = None,
        stat_result: t.Optional[os.stat_result] = None,
        method: t.Optional[str] = None,
    ) -> None:
        assert aiofiles is not None, "'aiofiles' must be installed to use FileResponse"
        self.path = path
        self.range = range
        self.filename = filename
        self.send_header_only = method is not None and method.upper() == "HEAD"
        self.media_type = media_type or guess_type(filename or path)[0] or "text/plain"
        self.init_headers(headers or {})
        if self.filename is not None:
            content_disposition_filename = quote(self.filename)
            self.headers.setdefault("content-disposition", (
                f"attachment; filename*=utf-8''{content_disposition_filename}"
                if content_disposition_filename != self.filename else 
                f'attachment; filename="{self.filename}"'
            ))
        self.stat_result = stat_result

    def set_range_headers(self, range: ClosedRange) -> None:
        assert self.stat_result
        total_length = self.stat_result.st_size
        content_length = len(range)
        self.headers["content-range"] = f"bytes {range.start}-{range.end}/{total_length}"
        self.headers["content-length"] = str(content_length)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if self.stat_result is None:
            try:
                self.stat_result = stat_result = await aio_stat(self.path)
            except FileNotFoundError:
                raise RuntimeError(f"File at path {self.path} does not exist.")
            else:
                if not stat.S_ISREG(stat_result.st_mode):
                    raise RuntimeError(f"File at path {self.path} is not a file.")

        byte_range = self.range.clamp(0, self.stat_result.st_size - 1)
        self.set_range_headers(byte_range)

        async with aiofiles.open(self.path, mode="rb") as file:
            await file.seek(byte_range.start)
            await send({
                "type": "http.response.start",
                "status": 206,
                "headers": self.raw_headers,
            })
            if self.send_header_only or not byte_range:
                await send({"type": "http.response.body", "body": b"", "more_body": False})
                return

            remaining_bytes = len(byte_range)
            while remaining_bytes > 0:
                chunk_size = min(self.chunk_size, remaining_bytes)
                chunk = await file.read(chunk_size)
                remaining_bytes -= len(chunk)
                await send({
                    "type": "http.response.body",
                    "body": chunk,
                    "more_body": remaining_bytes > 0,
                })


class RangedStaticFiles(StaticFiles):
    def file_response(
        self,
        full_path: PathLike,
        stat_result: os.stat_result,
        scope: Scope,
        status_code: int = 200,
    ) -> Response:
        if Headers(scope=scope).get("range"):
            response = self.ranged_file_response(full_path, stat_result=stat_result, scope=scope)
        else:
            response = super().file_response(full_path, stat_result=stat_result, scope=scope, status_code=status_code)
        response.headers["accept-ranges"] = "bytes"
        return response

    def ranged_file_response(
        self,
        full_path: PathLike,
        stat_result: os.stat_result,
        scope: Scope,
    ) -> Response:
        match = RANGE_REGEX.search(Headers(scope=scope)["range"])
        if not match:
            raise HTTPException(400)
        start, end = match.group("start"), match.group("end")
        range = OpenRange(int(start), int(end) if end else None)
        return RangedFileResponse(full_path, range, stat_result=stat_result, method=scope["method"])
