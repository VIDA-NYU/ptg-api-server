from fastapi import Request
#from fastapi.staticfiles import StaticFiles
from app.auth import UserAuth, oauth2
from app.range_static import RangedStaticFiles


class AuthStaticFiles(RangedStaticFiles):
    async def __call__(self, scope, receive, send) -> None:
        assert scope["type"] == "http"
        #request = Request(scope, receive)
        #await UserAuth.require_authorization(await oauth2(request))
        await super().__call__(scope, receive, send)
