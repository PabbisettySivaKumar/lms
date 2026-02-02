"""
Audit service: records user actions to the audit_logs table for compliance and support.
Uses affected_entity_type / affected_entity_id for the record that was affected by the action.
"""
from datetime import date, datetime
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession  # type: ignore
from backend.models import AuditLog


def _json_safe(obj: Any) -> Any:
    """Convert values to JSON-serializable form for MySQL JSON column."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, (datetime, date)):
        return obj.isoformat() if hasattr(obj, "isoformat") else str(obj)
    if hasattr(obj, "value"):  # enum
        return obj.value
    if isinstance(obj, (str, int, float, bool)):
        return obj
    return str(obj)


async def log_action(
    db: AsyncSession,
    action: str,
    affected_entity_type: str,
    *,
    user_id: Optional[int] = None,
    affected_entity_id: Optional[int] = None,
    old_values: Optional[dict[str, Any]] = None,
    new_values: Optional[dict[str, Any]] = None,
    actor_email: Optional[str] = None,
    actor_employee_id: Optional[str] = None,
    actor_full_name: Optional[str] = None,
    actor_role: Optional[str] = None,
    summary: Optional[str] = None,
    request_method: Optional[str] = None,
    request_path: Optional[str] = None,
) -> None:
    """
    Write an audit log entry. Call before commit (same transaction).
    affected_entity_type = kind of record affected (USER, LEAVE, POLICY, HOLIDAY, COMP_OFF, JOB, BALANCE).
    affected_entity_id   = primary key of that record (e.g. leave id, user id).
    """
    # Ensure old_values/new_values are JSON-serializable for MySQL
    old_safe = _json_safe(old_values) if old_values is not None else None
    new_safe = _json_safe(new_values) if new_values is not None else None

    entry = AuditLog(
        user_id=user_id,
        action=action,
        affected_entity_type=affected_entity_type,
        affected_entity_id=affected_entity_id,
        old_values=old_safe,
        new_values=new_safe,
        actor_email=actor_email,
        actor_employee_id=actor_employee_id,
        actor_full_name=actor_full_name,
        actor_role=actor_role,
        summary=summary,
        request_method=request_method,
        request_path=request_path,
    )
    db.add(entry)
