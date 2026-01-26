from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.database import SessionLocal
from app.db.models.login_log import RequestLog

class RequestLogMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):
        response = None
        error = None

        try:
            response = await call_next(request)
            return response
        except Exception as e:
            error = e
            raise
        finally:
            db = SessionLocal()
            try:
                suspicious_paths = [
                    "/wp-admin",
                    "/admin.php",
                    "/config.php",
                    "/autodiscover",
                    "/.env",
                    "/phpmyadmin"
                ]

                path = request.url.path.lower()
                is_suspicious = any(p in path for p in suspicious_paths)

                log = RequestLog(
                    ip_address=request.client.host if request.client else None,
                    method=request.method,
                    path=request.url.path,
                    status_code=response.status_code if response else 500,
                    user_agent=request.headers.get("user-agent"),
                    is_suspicious=is_suspicious,
                )

                db.add(log)
                db.commit()
            finally:
                db.close()
