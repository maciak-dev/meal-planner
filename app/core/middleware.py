from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from app.core.database import SessionLocal
from app.core.ip_block import is_ip_blocked

class IPBlockMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):
        ip = request.client.host

        db = SessionLocal()
        try:
            if is_ip_blocked(db, ip):
                return JSONResponse(
                    status_code=403,
                    content={"detail": "IP blocked due to too many failed login attempts"}
                )
        finally:
            db.close()

        return await call_next(request)
