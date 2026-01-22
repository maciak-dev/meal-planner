from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.db.models.login_log import LoginLog
from app.core.dependencies import super_admin_required

router = APIRouter()

@router.get("/admin/login-logs")
def login_logs(request: Request,
               db: Session = Depends(get_db),
               user=Depends(super_admin_required)):

    logs = (
        db.query(LoginLog)
        .order_by(LoginLog.created_at.desc())
        .limit(200)
        .all()
    )

    return templates.TemplateResponse(
        "admin/login_logs.html",
        {"request": request, "logs": logs}
    )
