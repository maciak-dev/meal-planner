from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from app.core.database import SessionLocal
from app.core.ip_block import is_ip_blocked

class IPBlockMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):
        request.state.blocked = False
        path = request.url.path

        # 1️⃣ infrastruktura MUSI działać
        if path.startswith((
            "/static",
            "/favicon.ico",
        )):
            return await call_next(request)

        # 2️⃣ login MUSI być dostępny
        if path in ("/login", "/logout"):
            return await call_next(request)

        # 3️⃣ teraz dopiero sprawdzamy blokadę IP
        ip = request.client.host

        db = SessionLocal()
        try:
            if is_ip_blocked(db, ip):
                request.state.blocked = True
                return JSONResponse(status_code=404, content={"detail": "Not Found"})
        finally:
            db.close()

        return await call_next(request)
