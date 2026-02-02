"""
User-action logging: writes who did what to the application log (file + console).
Use this so logs show e.g. "Employee X logged in" and "User X applied for leave".
"""
import logging
from typing import Any, Optional

ACTION_LOGGER = logging.getLogger("lms.actions")


def _user_context(
    user_id: Optional[int] = None,
    email: Optional[str] = None,
    employee_id: Optional[str] = None,
    full_name: Optional[str] = None,
    role: Optional[str] = None,
) -> str:
    parts = []
    if user_id is not None:
        parts.append(f"user_id={user_id}")
    if email:
        parts.append(f"email={email}")
    if employee_id:
        parts.append(f"employee_id={employee_id}")
    if full_name:
        parts.append(f"name={full_name!r}")
    if role:
        parts.append(f"role={role}")
    return " | ".join(parts) if parts else "anonymous"


def log_user_action(
    action: str,
    *,
    user_id: Optional[int] = None,
    email: Optional[str] = None,
    employee_id: Optional[str] = None,
    full_name: Optional[str] = None,
    role: Optional[str] = None,
    **details: Any,
) -> None:
    """
    Log a user action to the application log (logs/app.log and console).
    Use after login and after key actions (apply leave, cancel, approve, etc.).

    Example:
        log_user_action("LOGIN", user_id=user.id, email=user.email, role="employee")
        log_user_action("APPLIED_LEAVE", user_id=user.id, email=user.email, role=user.role,
                        leave_id=5, type="CASUAL", start_date="2025-01-01")
    """
    ctx = _user_context(
        user_id=user_id,
        email=email,
        employee_id=employee_id,
        full_name=full_name,
        role=role,
    )
    extra_parts = [f"{k}={v!r}" if isinstance(v, str) else f"{k}={v}" for k, v in details.items()]
    extra = " " + " ".join(extra_parts) if extra_parts else ""
    message = f"USER_ACTION | {ctx} | {action}{extra}"
    ACTION_LOGGER.info(message)
