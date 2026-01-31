from fastapi import APIRouter, Depends, Request, Query
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.core.database import get_db
from app.db.models.login_log import LoginLog, RequestLog
from app.core.dependencies import super_admin_required

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/login-logs", dependencies=[Depends(super_admin_required)])
def login_logs(
    range: str = Query("today", pattern="^(today|7d|30d|all)$"),
    limit: int = Query(200, ge=1, le=2000),
    db: Session = Depends(get_db),
):
    q = db.query(LoginLog)

    now = datetime.utcnow()

    if range == "today":
        q = q.filter(LoginLog.created_at >= now.replace(
            hour=0, minute=0, second=0, microsecond=0
        ))
    elif range == "7d":
        q = q.filter(LoginLog.created_at >= now - timedelta(days=7))
    elif range == "30d":
        q = q.filter(LoginLog.created_at >= now - timedelta(days=30))
    # "all" → brak filtra

    logs = (
        q.order_by(LoginLog.created_at.desc())
         .limit(limit)
         .all()
    )

    return [
        {
            "username": log.username,
            "ip_address": log.ip_address,
            "success": log.success,
            "created_at": log.created_at.isoformat(),
            "user_agent": log.user_agent,
        }
        for log in logs
    ]



@router.get("/requests", dependencies=[Depends(super_admin_required)])
def get_request_logs(
    range: str = Query("today", pattern="^(today|7d|30d|all)$"),
    limit: int = Query(2000, ge=1, le=2000),
    db: Session = Depends(get_db),
):
    q = db.query(RequestLog)

    now = datetime.utcnow()

    if range == "today":
        q = q.filter(RequestLog.created_at >= now.replace(
            hour=0, minute=0, second=0, microsecond=0
        ))
    elif range == "7d":
        q = q.filter(RequestLog.created_at >= now - timedelta(days=7))
    elif range == "30d":
        q = q.filter(RequestLog.created_at >= now - timedelta(days=30))

    logs = (
        q.order_by(RequestLog.created_at.desc())
         .limit(limit)
         .all()
    )

    return [
        {
            "path": log.path,
            "ip_address": log.ip_address,
            "status": log.status_code,
            "is_suspicious": log.is_suspicious,
            "created_at": log.created_at.isoformat(),
            "user_agent": log.user_agent,
        }
        for log in logs
    ]
