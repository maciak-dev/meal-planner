from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.db.models.login_log import LoginLog, RequestLog
from app.core.dependencies import super_admin_required

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/login-logs", dependencies=[Depends(super_admin_required)])
def login_logs(db: Session = Depends(get_db)):
    logs = (
        db.query(LoginLog)
        .order_by(LoginLog.created_at.desc())
        .limit(200)
        .all()
    )

    # Konwertujemy na dict dla JSON
    return [
        {
            "username": log.username,
            "ip_address": log.ip_address,
            "success": log.success,
            "created_at": log.created_at.isoformat(),
            "user_agent": log.user_agent
        }
        for log in logs
    ]


@router.get("/requests", dependencies=[Depends(super_admin_required)])
def get_request_logs(db: Session = Depends(get_db)):
    logs = (
        db.query(RequestLog)
        .order_by(RequestLog.created_at.desc())
        .limit(200)
        .all()
    )
    return [
        {
            "path": log.path,
            "ip_address": log.ip_address,
            "status": log.status_code,
            "is_suspicious": log.is_suspicious,
            "created_at": log.created_at.isoformat(),
            "user_agent": log.user_agent
        }
        for log in logs
    ]
