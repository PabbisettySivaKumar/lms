import logging
import os
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from datetime import date, timedelta
from typing import List, Union, Optional
from backend.utils.id_utils import to_int_id

from backend.db import get_db, AsyncSessionLocal
from backend.models import (
    User as UserModel, LeaveRequest as LeaveRequestModel, CompOffClaim as CompOffClaimModel, 
    LeaveStatusEnum, LeaveTypeEnum, CompOffStatusEnum
)
from backend.models.leave import (
    LeaveRequestCreate, LeaveStatus, LeaveType, 
    CompOffClaimCreate, CompOffStatus
)
from backend.models.user import UserRole
from backend.models import UserSchema
from backend.routes.auth import get_current_user_email, verify_admin, create_scope_dependency
from backend.routes.users import user_model_to_pydantic
from backend.utils.scopes import Scope
from backend.services.email import send_email
from backend.services.audit import log_action as audit_log_action
from backend.utils.action_log import log_user_action
from backend.utils.leave_utils import (
    calculate_deductible_days_optimized,
    determine_approver,
    check_leave_overlap,
    check_balance_sufficient,
    update_user_balance,
    get_balance_field
)
from sqlalchemy import select, and_, or_, func, desc  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession  # type: ignore
from sqlalchemy.orm import selectinload  # type: ignore
import csv
import io
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/leaves", tags=["Leaves"])

async def get_current_user(email: str = Depends(get_current_user_email), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(UserModel).where(UserModel.email == email).options(selectinload(UserModel.profile))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return await user_model_to_pydantic(user, db)

# Removed: calculate_deductible_days() - now using calculate_deductible_days_optimized from leave_utils

@router.post("/apply", response_model=dict)
async def apply_leave(
    request: Request,
    leave: LeaveRequestCreate,
    background_tasks: BackgroundTasks,
    user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        # 0. Prevent EARNED as a new leave type (use CASUAL instead)
        if leave.type == LeaveType.EARNED:
            raise HTTPException(
                status_code=400,
                detail="Earned Leave is no longer a separate leave type. Please use Casual/Earned Leave (CASUAL) instead."
            )
        
        # 1. Validation specific to types
        if leave.type == LeaveType.SABBATICAL:
            # Sabbatical: end_date can be None (Open-ended) or set.
            pass
        elif leave.type == LeaveType.MATERNITY:
            # Maternity: 180 days fixed. Frontend sends date, but let's enforce or calculate?
            # User requirement: "Auto-Calculation: Automatically calculate and set the end_date to exactly 180 days"
            # Since frontend sends it, we trust it or re-calc. Let's re-calc to be safe.
            calculated_end = leave.start_date + timedelta(days=179)
            leave.end_date = calculated_end
        else:
            # Standard: End date required
            if not leave.end_date:
                 raise HTTPException(status_code=400, detail="End date is required for this leave type")
            if leave.start_date > leave.end_date:
                raise HTTPException(status_code=400, detail="End date must be after start date")

        # 2. Overlap Check - using optimized utility function
        # Note: check_leave_overlap needs to be updated to work with SQLAlchemy
        # For now, we'll pass db and let it query directly
        new_start = str(leave.start_date)
        new_end = str(leave.end_date) if leave.end_date else None
        await check_leave_overlap(user.id, new_start, new_end, db)
            
        # 3. Balance & Deductible Calculation
        deductible_days = 0.0
        
        if leave.type in [LeaveType.CASUAL, LeaveType.SICK, LeaveType.COMP_OFF, LeaveType.WFH]:
            if not leave.end_date:
                raise HTTPException(status_code=400, detail="End date is required for this leave type")
            deductible_days = await calculate_deductible_days_optimized(leave.start_date, leave.end_date, db)
            
            # Balance Check - using optimized utility function
            await check_balance_sufficient(user, leave.type, deductible_days, db)
        
        # Maternity / Sabbatical = 0 deductible (or handled purely as status without balance)
        # User said "Ensure maternity does not deduct from standard CL/SL".
        
        
        # DETERMINE APPROVER - using optimized utility function
        # Returns user.id (integer) for foreign key compatibility
        approver_user_id, approver_email = await determine_approver(user, db)
        
        # Convert leave type enum to database enum
        leave_type_enum = LeaveTypeEnum[leave.type.value]
        status_enum = LeaveStatusEnum.PENDING
        
        # Save to DB using SQLAlchemy
        try:
            new_leave = LeaveRequestModel(  # type: ignore[call-arg]
                applicant_id=user.id,
                approver_id=approver_user_id,
                type=leave_type_enum,
                start_date=leave.start_date,
                end_date=leave.end_date,
                deductible_days=deductible_days,
                status=status_enum,
                reason=leave.reason
            )
            db.add(new_leave)
            await db.flush()  # Flush to get the ID
            leave_id = new_leave.id
            await audit_log_action(
                db,
                "CREATE_LEAVE",
                "LEAVE",
                user_id=user.id,
                affected_entity_id=leave_id,
                new_values={
                    "type": leave.type.value,
                    "start_date": str(leave.start_date),
                    "end_date": str(leave.end_date) if leave.end_date else None,
                    "deductible_days": deductible_days,
                    "status": "PENDING",
                },
                actor_email=user.email,
                actor_employee_id=user.employee_id,
                actor_full_name=user.full_name,
                actor_role=getattr(user, "role", None),
                summary=f"{user.full_name} applied for leave ({leave.type.value}, {deductible_days} days)",
                request_method=request.method,
                request_path=request.url.path,
            )
            await db.commit()
            log_user_action(
                "APPLIED_LEAVE",
                user_id=user.id,
                email=user.email,
                employee_id=user.employee_id,
                full_name=user.full_name,
                role=getattr(user, "role", None),
                leave_id=leave_id,
                type=leave.type.value,
                start_date=str(leave.start_date),
                deductible_days=deductible_days,
            )
        except Exception as db_error:
            await db.rollback()
            logger.exception("Database error in apply_leave: %s", db_error)
            raise HTTPException(
                status_code=500,
                detail=f"Database error: {str(db_error)}"
            )
        
        # NOTIFICATION - using background task for non-blocking email
        if approver_email:
            frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
            
            dates_str = f"{leave.start_date}"
            if leave.end_date:
                 dates_str += f" to {leave.end_date}"
            
            # Leave Type Formatting
            leave_type_map = {
                "CASUAL": "Casual/Earned Leave",
                "SICK": "Sick Leave",
                "EARNED": "Casual/Earned Leave",  # For backward compatibility with existing EARNED leaves
                "WFH": "Work From Home",
                "COMP_OFF": "Comp Off",
                "MATERNITY": "Maternity Leave",
                "SABBATICAL": "Sabbatical Leave"
            }
            formatted_type = leave_type_map.get(leave.type, leave.type)

            email_body = f"""
            <html>
                <body>
                    <p>Hello,</p>
                    <p>This is to inform you that <strong>{user.full_name}</strong> has requested a <strong>{formatted_type}</strong> on the following date(s):<br>
                    {dates_str}</p>
                    
                    <p>They left the following remark:<br>
                    <em>{leave.reason or 'N/A'}</em></p>
                    
                    <p>To approve or reject these requests, please click the link below:</p>
                    
                    <p>
                        <a href="{frontend_url}/dashboard/team" 
                        style="color: #2563EB; text-decoration: underline; font-weight: bold;">
                        Click here to view {user.full_name}'s request
                        </a>
                    </p>

                    <p>Thanks,<br>
                    {user.full_name}</p>
                </body>
            </html>
            """

            background_tasks.add_task(
                send_email,
                to_email=approver_email, 
                subject=f"New Leave Request from {user.full_name}",
                body=email_body,
                subtype="html"
            )
            
        return {
            "message": "Leave application submitted", 
            "id": str(leave_id), 
            "deductible_days": deductible_days,
            "assigned_approver": approver_user_id
        }
    except HTTPException:
        # Re-raise HTTPExceptions as-is (they already have proper status codes and details)
        raise
    except Exception as e:
        logger.exception("Error in apply_leave: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.post("/claim-comp-off", response_model=dict)
async def claim_comp_off(
    request: Request,
    claim: CompOffClaimCreate,
    background_tasks: BackgroundTasks,
    user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if claim.work_date > date.today():
        raise HTTPException(status_code=400, detail="Cannot claim comp-off for future dates")
    
    # Determine Approver - using optimized utility function
    # Returns user.id (integer) for foreign key compatibility
    approver_user_id, approver_email = await determine_approver(user, db)

    # Create comp-off claim using SQLAlchemy
    new_claim = CompOffClaimModel(  # type: ignore[call-arg]
        claimant_id=user.id,
        approver_id=approver_user_id,
        work_date=claim.work_date,
        reason=claim.reason,
        status=CompOffStatusEnum.PENDING
    )
    db.add(new_claim)
    await db.flush()  # Flush to get the ID
    claim_id = new_claim.id
    await audit_log_action(
        db,
        "CREATE_COMP_OFF",
        "COMP_OFF",
        user_id=user.id,
        affected_entity_id=claim_id,
        new_values={"work_date": str(claim.work_date), "reason": claim.reason, "status": "PENDING"},
        actor_email=user.email,
        actor_employee_id=user.employee_id,
        actor_full_name=user.full_name,
        actor_role=getattr(user, "role", None),
        summary=f"{user.full_name} claimed comp-off for {claim.work_date}",
        request_method=request.method,
        request_path=request.url.path,
    )
    await db.commit()
    log_user_action(
        "CLAIMED_COMP_OFF",
        user_id=user.id,
        email=user.email,
        employee_id=user.employee_id,
        full_name=user.full_name,
        role=getattr(user, "role", None),
        comp_off_id=claim_id,
        work_date=str(claim.work_date),
    )
    # NOTIFICATION - using background task for non-blocking email
    if approver_email:
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        approval_link = f"{frontend_url}/dashboard/team"
        
        email_body = f"""
        <html>
            <body>
                <p>Hello,</p>
                <p>This is to inform you that <strong>{user.full_name}</strong> has requested a <strong>Comp Off</strong> on the following date(s):<br>
                {claim.work_date}</p>
                
                <p>They left the following remark:<br>
                {claim.reason}</p>
                
                <p>To approve or reject these requests, please click the link below:</p>
                
                <p><a href="{approval_link}">Click here to view {user.full_name}'s request</a></p>
                
                <p>Thanks,<br>
                {user.full_name}</p>
            </body>
        </html>
        """
        
        background_tasks.add_task(
            send_email,
            to_email=approver_email,
            subject=f"New Comp-Off Claim from {user.full_name}",
            body=email_body,
            subtype="html"
        )
    
    return {"message": "Comp-off claim submitted", "id": str(claim_id), "assigned_approver": approver_user_id}

@router.patch("/action/{item_id}")
async def action_leave(
    request: Request,
    item_id: str,
    action: str,  # APPROVE or REJECT
    note: Optional[str] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    # Use scope-based auth for approve:leaves scope
    email: str = Depends(create_scope_dependency([Scope.APPROVE_LEAVES])),
    db: AsyncSession = Depends(get_db),
):
    if action not in ["APPROVE", "REJECT"]:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    # Get approver user object for additional checks (eager-load profile for user_model_to_pydantic)
    result = await db.execute(
        select(UserModel).where(UserModel.email == email).options(selectinload(UserModel.profile))
    )
    approver_model = result.scalar_one_or_none()
    if not approver_model:
        raise HTTPException(status_code=404, detail="Approver not found")
    approver = await user_model_to_pydantic(approver_model, db)
        
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    # Convert item_id to integer
    item_id_int = to_int_id(item_id)
    if not item_id_int:
        raise HTTPException(status_code=400, detail="Invalid request ID")
    
    # Try finding in Leave Requests first
    item_type = "leave"
    result = await db.execute(select(LeaveRequestModel).where(LeaveRequestModel.id == item_id_int))
    item = result.scalar_one_or_none()
    
    # If not found, try Comp-Off Claims
    if not item:
        item_type = "comp_off"
        result = await db.execute(select(CompOffClaimModel).where(CompOffClaimModel.id == item_id_int))
        item = result.scalar_one_or_none()
        
    if not item:
        raise HTTPException(status_code=404, detail="Request not found")
        
    current_status = item.status.value if hasattr(item.status, 'value') else str(item.status)
    # Use enum values consistently instead of string comparison
    if current_status not in [LeaveStatus.PENDING, CompOffStatus.PENDING, LeaveStatus.CANCELLATION_REQUESTED]:
        raise HTTPException(status_code=400, detail="Request is not pending or cancellation requested")

    # STRICT PERMISSION CHECK
    # Rule 1: Assigned Manager (check if approver_id matches)
    # Get approver's employee_id for comparison
    approver_result = await db.execute(select(UserModel).where(UserModel.id == approver.id))
    approver_db = approver_result.scalar_one_or_none()
    if not approver_db:
        raise HTTPException(status_code=404, detail="Approver not found in database")
    
    is_assigned_manager = False
    if item_type == "leave":
        is_assigned_manager = (item.approver_id == approver.id)
    else:
        is_assigned_manager = (item.approver_id == approver.id)
    
    # Rule 2: God Mode (Admin, Founder, HR) - check via role
    # Get user's role from user_roles table
    from backend.models import UserRole as UserRoleModel, Role
    role_result = await db.execute(
        select(Role.name)
        .join(UserRoleModel, Role.id == UserRoleModel.role_id)
        .where(and_(UserRoleModel.user_id == approver.id, UserRoleModel.is_active == True))
    )
    role_name = role_result.scalar_one_or_none()
    is_super_approver = role_name in [UserRole.ADMIN.value, UserRole.FOUNDER.value, UserRole.CO_FOUNDER.value, UserRole.HR.value] if role_name else False
    
    if not (is_assigned_manager or is_super_approver):
         raise HTTPException(status_code=403, detail="You are not authorized to approve this request")

    # EXECUTE ACTION
    if item_type == "leave":
        new_status_enum = LeaveStatusEnum.APPROVED if action == "APPROVE" else LeaveStatusEnum.REJECTED
        
        # Handle Cancellation Approval
        if current_status == LeaveStatus.CANCELLATION_REQUESTED:
             if action == "APPROVE":
                 new_status_enum = LeaveStatusEnum.CANCELLED
             else:
                 # Rejecting cancellation means it goes back to APPROVED
                 new_status_enum = LeaveStatusEnum.APPROVED
                 
        applicant_id = item.applicant_id
        
        # LOGIC:
        # 1. PENDING -> APPROVED: Deduct
        # 2. CANCELLATION_REQUESTED -> CANCELLED: Refund
        
        if current_status == LeaveStatus.PENDING and new_status_enum == LeaveStatusEnum.APPROVED:
            # Deduct balance - using optimized utility function
            deductible = float(item.deductible_days)
            leave_type = LeaveType(item.type.value if hasattr(item.type, 'value') else str(item.type))
            
            # Check balance before deducting (eager-load profile for user_model_to_pydantic)
            applicant_result = await db.execute(
                select(UserModel).where(UserModel.id == applicant_id).options(selectinload(UserModel.profile))
            )
            applicant = applicant_result.scalar_one_or_none()
            if not applicant:
                raise HTTPException(status_code=404, detail="Applicant not found")
            
            applicant_user = await user_model_to_pydantic(applicant, db)
            await check_balance_sufficient(applicant_user, leave_type, deductible, db)
            
            # Deduct using utility function
            await update_user_balance(
                applicant_id, leave_type, deductible, "deduct", db,
                related_leave_id=item.id, changed_by=approver.id,
            )

        elif current_status == LeaveStatus.CANCELLATION_REQUESTED and new_status_enum == LeaveStatusEnum.CANCELLED:
            # Refund balance - using optimized utility function
            deductible = float(item.deductible_days)
            leave_type = LeaveType(item.type.value if hasattr(item.type, 'value') else str(item.type))
            await update_user_balance(
                applicant_id, leave_type, deductible, "refund", db,
                related_leave_id=item.id, changed_by=approver.id,
            )
        
        # Update leave request
        item.status = new_status_enum
        item.approver_id = approver.id
        item.manager_note = note
        if new_status_enum == LeaveStatusEnum.APPROVED:
            from datetime import datetime
            item.approved_at = datetime.utcnow()
        elif new_status_enum == LeaveStatusEnum.REJECTED:
            from datetime import datetime
            item.rejected_at = datetime.utcnow()
        await audit_log_action(
            db,
            "APPROVE_LEAVE" if action == "APPROVE" else "REJECT_LEAVE",
            "LEAVE",
            user_id=approver.id,
            affected_entity_id=item.id,
            old_values={"status": current_status},
            new_values={"status": new_status_enum.value, "note": note},
            actor_email=approver.email,
            actor_employee_id=approver.employee_id,
            actor_full_name=approver.full_name,
            actor_role=getattr(approver, "role", None),
            summary=f"{approver.full_name} {action.lower()}ed leave request #{item.id}",
            request_method=request.method,
            request_path=request.url.path,
        )
        await db.commit()
        log_user_action(
            "APPROVED_LEAVE" if action == "APPROVE" else "REJECTED_LEAVE",
            user_id=approver.id,
            email=approver.email,
            employee_id=approver.employee_id,
            full_name=approver.full_name,
            role=getattr(approver, "role", None),
            leave_id=item.id,
            applicant_id=applicant_id,
            new_status=new_status_enum.value,
        )
    else: # comp_off
        new_status_enum = CompOffStatusEnum.APPROVED if action == "APPROVE" else CompOffStatusEnum.REJECTED
        applicant_id = item.claimant_id
        
        if new_status_enum == CompOffStatusEnum.APPROVED:
            # Increment comp-off balance in user_leave_balances table and record history
            from backend.models import UserLeaveBalance
            from backend.services.balance_history import record_balance_change
            from backend.models.enums import BalanceChangeTypeEnum
            balance_result = await db.execute(
                select(UserLeaveBalance).where(
                    and_(UserLeaveBalance.user_id == applicant_id, UserLeaveBalance.leave_type == LeaveTypeEnum.COMP_OFF)
                )
            )
            balance = balance_result.scalar_one_or_none()
            prev_comp = float(balance.balance) if balance else 0.0
            if balance:
                balance.balance = prev_comp + 1.0
            else:
                new_balance = UserLeaveBalance(
                    user_id=applicant_id,
                    leave_type=LeaveTypeEnum.COMP_OFF,
                    balance=1.0
                )
                db.add(new_balance)
            await record_balance_change(
                db, applicant_id, LeaveTypeEnum.COMP_OFF, prev_comp, prev_comp + 1.0,
                BalanceChangeTypeEnum.ACCRUAL, reason="Comp-off claim approved",
                related_leave_id=None, changed_by=approver.id,
            )
            
        # Update comp-off claim
        item.status = new_status_enum
        item.approver_id = approver.id
        item.manager_note = note
        if new_status_enum == CompOffStatusEnum.APPROVED:
            from datetime import datetime
            item.approved_at = datetime.utcnow()
        current_status_comp = item.status.value if hasattr(item.status, "value") else str(item.status)
        await audit_log_action(
            db,
            "APPROVE_COMP_OFF" if action == "APPROVE" else "REJECT_COMP_OFF",
            "COMP_OFF",
            user_id=approver.id,
            affected_entity_id=item.id,
            old_values={"status": current_status_comp},
            new_values={"status": new_status_enum.value, "note": note},
            actor_email=approver.email,
            actor_employee_id=approver.employee_id,
            actor_full_name=approver.full_name,
            actor_role=getattr(approver, "role", None),
            summary=f"{approver.full_name} {action.lower()}ed comp-off claim #{item.id}",
            request_method=request.method,
            request_path=request.url.path,
        )
        await db.commit()
        log_user_action(
            "APPROVED_COMP_OFF" if action == "APPROVE" else "REJECTED_COMP_OFF",
            user_id=approver.id,
            email=approver.email,
            employee_id=approver.employee_id,
            full_name=approver.full_name,
            role=getattr(approver, "role", None),
            comp_off_id=item.id,
            claimant_id=applicant_id,
            new_status=new_status_enum.value,
        )

    # NOTIFICATION — send from manager's email (from DB), not MAIL_FROM
    applicant_result = await db.execute(select(UserModel).where(UserModel.id == applicant_id))
    applicant = applicant_result.scalar_one_or_none()
    if applicant and applicant.email:
        manager_email = getattr(approver_model, "email", None) or getattr(approver, "email", None) or ""
        status_color = "#16a34a" if action == "APPROVE" else "#dc2626"
        action_text = "APPROVED" if action == "APPROVE" else "REJECTED"

        email_body = f"""
        <html>
            <body>
                <p>Hello {applicant.full_name},</p>
                <p>Your leave request has been <strong style="color: {status_color};">{action_text}</strong> by {approver.full_name}.</p>
                
                <p><strong>Manager's Note:</strong><br>
                <em>{note or 'None'}</em></p>
                
                <p>You can view your leave status at:</p>
                <p>
                    <a href="{frontend_url}/dashboard/employee/leaves" style="background-color: #2563eb; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">View My Requests</a>
                </p>
                
                <p>Thanks,<br>
                {approver.full_name}</p>
            </body>
        </html>
        """

        if background_tasks:
            background_tasks.add_task(
                send_email,
                to_email=applicant.email,
                subject=f"Leave Request {action_text}",
                body=email_body,
                subtype="html",
                from_email=manager_email,
            )
        else:
            await send_email(
                to_email=applicant.email,
                subject=f"Leave Request {action_text}",
                body=email_body,
                subtype="html",
                from_email=manager_email,
            )

    new_status_str = new_status_enum.value if hasattr(new_status_enum, 'value') else str(new_status_enum)
    return {"message": f"Request {new_status_str}"}

@router.post("/{leave_id}/cancel")
async def cancel_leave(
    request: Request,
    leave_id: str,
    user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Convert leave_id to integer
    leave_id_int = to_int_id(leave_id)
    if not leave_id_int:
        raise HTTPException(status_code=400, detail="Invalid leave ID")
    
    # Find the leave
    result = await db.execute(
        select(LeaveRequestModel).where(
            and_(LeaveRequestModel.id == leave_id_int, LeaveRequestModel.applicant_id == user.id)
        )
    )
    leave = result.scalar_one_or_none()
    
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")
        
    current_status = leave.status.value if hasattr(leave.status, 'value') else str(leave.status)
    
    # Case A: Pending -> Delete & Refund (if applicable - actually PENDING didn't deduct yet in current logic? 
    # WAIT: allow me to check apply_leave logic. 
    # In apply_leave: "deductible_days" is calculated but balance is NOT deducted. 
    # Balance is deducted in action_leave when APPROVED.
    # So for PENDING, we just delete or mark cancelled. No refund needed really, but let's be safe.
    
    if current_status == LeaveStatus.PENDING:
        # Just update status to CANCELLED or delete? User asked to "Delete or mark as Withdrawn".
        # Let's mark as CANCELLED to keep history.
        leave.status = LeaveStatusEnum.CANCELLED
        await audit_log_action(
            db,
            "CANCEL_LEAVE",
            "LEAVE",
            user_id=user.id,
            affected_entity_id=leave.id,
            old_values={"status": current_status},
            new_values={"status": "CANCELLED"},
            actor_email=user.email,
            actor_employee_id=user.employee_id,
            actor_full_name=user.full_name,
            actor_role=getattr(user, "role", None),
            summary=f"{user.full_name} withdrew leave request #{leave.id} (was {current_status})",
            request_method=request.method,
            request_path=request.url.path,
        )
        await db.commit()
        log_user_action(
            "CANCELLED_LEAVE",
            user_id=user.id,
            email=user.email,
            employee_id=user.employee_id,
            full_name=user.full_name,
            role=getattr(user, "role", None),
            leave_id=leave.id,
            previous_status=current_status,
        )
        return {"message": "Leave withdrawn successfully."}
        
    # Case B: Approved -> Immediate Cancel + Refund
    elif current_status == LeaveStatus.APPROVED:
        # Refund Policy: Allow immediate self-cancellation
        
        # Refund Balance - using optimized utility function
        deductible = float(leave.deductible_days)
        leave_type = LeaveType(leave.type.value if hasattr(leave.type, 'value') else str(leave.type))
        
        # Only refund if it was a deductible type (Maternity/Sabbatical are 0 anyway)
        if deductible > 0:
            await update_user_balance(
                user.id, leave_type, deductible, "refund", db,
                related_leave_id=leave.id, changed_by=user.id,
            )

        # Update Status
        leave.status = LeaveStatusEnum.CANCELLED
        await audit_log_action(
            db,
            "CANCEL_LEAVE",
            "LEAVE",
            user_id=user.id,
            affected_entity_id=leave.id,
            old_values={"status": current_status, "type": leave.type.value if hasattr(leave.type, "value") else str(leave.type), "deductible_days": deductible},
            new_values={"status": "CANCELLED", "refunded_days": deductible},
            actor_email=user.email,
            actor_employee_id=user.employee_id,
            actor_full_name=user.full_name,
            actor_role=getattr(user, "role", None),
            summary=f"{user.full_name} cancelled approved leave #{leave.id} (refunded {deductible} days)",
            request_method=request.method,
            request_path=request.url.path,
        )
        await db.commit()
        log_user_action(
            "CANCELLED_LEAVE",
            user_id=user.id,
            email=user.email,
            employee_id=user.employee_id,
            full_name=user.full_name,
            role=getattr(user, "role", None),
            leave_id=leave.id,
            previous_status=current_status,
            refunded_days=deductible,
        )
        return {"message": "Leave cancelled and balance refunded."}
        
    # Case C: Rejected or already Cancelled
    else:
        raise HTTPException(status_code=400, detail="Cannot cancel this leave.")

@router.get("/pending", response_model=dict)
async def get_pending_requests(user: UserSchema = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Get user's role to check if they're admin/HR/founder
    from backend.models import UserRole as UserRoleModel, Role
    role_result = await db.execute(
        select(Role.name)
        .join(UserRoleModel, Role.id == UserRoleModel.role_id)
        .where(and_(UserRoleModel.user_id == user.id, UserRoleModel.is_active == True))
    )
    role_name = role_result.scalar_one_or_none()
    is_god_mode = role_name in [UserRole.ADMIN.value, UserRole.HR.value, UserRole.FOUNDER.value, UserRole.CO_FOUNDER.value] if role_name else False
    
    # LEAVES QUERY
    leave_query = select(LeaveRequestModel).where(LeaveRequestModel.status == LeaveStatusEnum.PENDING)
    if not is_god_mode:
        leave_query = leave_query.where(LeaveRequestModel.approver_id == user.id)
    
    result = await db.execute(leave_query)
    leaves_models = result.scalars().all()
    
    leaves = []
    applicant_ids = set()
    for l in leaves_models:
        applicant_ids.add(l.applicant_id)
        leaves.append({
            "id": str(l.id),
            "_id": str(l.id),
            "applicant_id": str(l.applicant_id),
            "type": l.type.value if hasattr(l.type, 'value') else str(l.type),
            "start_date": str(l.start_date),
            "end_date": str(l.end_date) if l.end_date else None,
            "status": l.status.value if hasattr(l.status, 'value') else str(l.status),
            "deductible_days": float(l.deductible_days),
            "reason": l.reason,
            "approver_id": str(l.approver_id) if l.approver_id else None,
        })
        
    # COMP OFF QUERY
    comp_off_query = select(CompOffClaimModel).where(CompOffClaimModel.status == CompOffStatusEnum.PENDING)
    if not is_god_mode:
        comp_off_query = comp_off_query.where(CompOffClaimModel.approver_id == user.id)
    
    result = await db.execute(comp_off_query)
    comp_off_models = result.scalars().all()
    
    comp_offs = []
    for c in comp_off_models:
        applicant_ids.add(c.claimant_id)
        comp_offs.append({
            "id": str(c.id),
            "_id": str(c.id),
            "claimant_id": str(c.claimant_id),
            "work_date": str(c.work_date),
            "status": c.status.value if hasattr(c.status, 'value') else str(c.status),
            "reason": c.reason,
            "approver_id": str(c.approver_id) if c.approver_id else None,
        })
        
    # Fetch Applicant Details
    users_map = {}
    if applicant_ids:
        result = await db.execute(select(UserModel).where(UserModel.id.in_(list(applicant_ids))))
        for u in result.scalars().all():
            users_map[str(u.id)] = u.full_name

    # Attach Names
    for l in leaves:
        l["applicant_name"] = users_map.get(l["applicant_id"], "Unknown")
        
    for c in comp_offs:
        c["applicant_name"] = users_map.get(c["claimant_id"], "Unknown")
        c["type"] = "COMP_OFF_GRANT" # Distinct from leave type COMP_OFF
        c["start_date"] = c["work_date"] # Normalize date for table
        c["end_date"] = c["work_date"]
        c["deductible_days"] = 1.0 # Earning 1 day

    return {
        "leaves": leaves,
        "comp_offs": comp_offs
    }

@router.get("/mine", response_model=dict)
async def get_my_leaves(
    skip: int = 0,
    limit: int = 20,
    user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's leaves with pagination.
    """
    # 1. Fetch Leaves with pagination
    leave_query = (
        select(LeaveRequestModel)
        .where(LeaveRequestModel.applicant_id == user.id)
        .order_by(desc(LeaveRequestModel.start_date))
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(leave_query)
    leaves_models = result.scalars().all()
    
    # Get total count
    count_query = select(func.count()).select_from(
        select(LeaveRequestModel).where(LeaveRequestModel.applicant_id == user.id).subquery()
    )
    total_result = await db.execute(count_query)
    total_leaves = total_result.scalar() or 0
    
    leaves = []
    for doc in leaves_models:
        leaves.append({
            "id": str(doc.id),
            "request_type": "leave",  # So frontend can call /leaves/:id/cancel only for leaves
            "start_date": str(doc.start_date),
            "end_date": str(doc.end_date) if doc.end_date else None,
            "type": doc.type.value if hasattr(doc.type, 'value') else str(doc.type),
            "status": doc.status.value.upper() if hasattr(doc.status, 'value') else str(doc.status).upper(),
            "deductible_days": float(doc.deductible_days)
        })

    # 2. Fetch Comp-Offs (for now, include all - can be paginated separately if needed)
    comp_off_query = (
        select(CompOffClaimModel)
        .where(CompOffClaimModel.claimant_id == user.id)
        .order_by(desc(CompOffClaimModel.work_date))
    )
    result = await db.execute(comp_off_query)
    comp_off_models = result.scalars().all()
    
    for doc in comp_off_models:
        leaves.append({
            "id": str(doc.id),
            "request_type": "comp_off",  # Different table - do not use for /leaves/:id/cancel
            "start_date": str(doc.work_date),
            "end_date": str(doc.work_date),  # Same day
            "type": "COMP_OFF",
            "status": doc.status.value.upper() if hasattr(doc.status, 'value') else str(doc.status).upper(),
            "deductible_days": 1.0  # Earning 1 day, effectively
        })

    return {
        "leaves": leaves,
        "total": total_leaves,
        "skip": skip,
        "limit": limit
    }

@router.get("/export/stats")
async def get_export_stats(
    start_date: date,
    end_date: date,
    email: str = Depends(create_scope_dependency([Scope.EXPORT_DATA])),
    db: AsyncSession = Depends(get_db)
):
    # 1. Count Approved Leaves
    leaves_count_query = select(func.count()).select_from(
        select(LeaveRequestModel).where(
            and_(
                LeaveRequestModel.status == LeaveStatusEnum.APPROVED,
                LeaveRequestModel.start_date >= start_date,
                LeaveRequestModel.start_date <= end_date
            )
        ).subquery()
    )
    result = await db.execute(leaves_count_query)
    leaves_count = result.scalar() or 0

    # 2. Count Approved Comp-Offs
    comp_off_count_query = select(func.count()).select_from(
        select(CompOffClaimModel).where(
            and_(
                CompOffClaimModel.status == CompOffStatusEnum.APPROVED,
                CompOffClaimModel.work_date >= start_date,
                CompOffClaimModel.work_date <= end_date
            )
        ).subquery()
    )
    result = await db.execute(comp_off_count_query)
    comp_off_count = result.scalar() or 0
    
    return {
        "leaves_count": leaves_count,
        "comp_off_count": comp_off_count,
        "total_records": leaves_count + comp_off_count
    }

@router.get("/export")
async def export_leaves(
    start_date: date,
    end_date: date,
    email: str = Depends(create_scope_dependency([Scope.EXPORT_DATA])),
    db: AsyncSession = Depends(get_db)
):
    # 1. Fetch Approved Leaves
    leaves_query = select(LeaveRequestModel).where(
        and_(
            LeaveRequestModel.status == LeaveStatusEnum.APPROVED,
            LeaveRequestModel.start_date >= start_date,
            LeaveRequestModel.start_date <= end_date
        )
    )
    result = await db.execute(leaves_query)
    leaves_models = result.scalars().all()
    leaves = [l for l in leaves_models]

    # 2. Fetch Approved Comp-Offs (work_date in range)
    comp_off_query = select(CompOffClaimModel).where(
        and_(
            CompOffClaimModel.status == CompOffStatusEnum.APPROVED,
            CompOffClaimModel.work_date >= start_date,
            CompOffClaimModel.work_date <= end_date
        )
    )
    result = await db.execute(comp_off_query)
    comp_off_models = result.scalars().all()
    comp_offs = [c for c in comp_off_models]

    # 3. Collect User IDs for fetching names (Applicants + Approvers)
    user_ids = set()
    for l in leaves:
        if l.applicant_id: user_ids.add(l.applicant_id)
        if l.approver_id: user_ids.add(l.approver_id)

    for c in comp_offs:
        if c.claimant_id: user_ids.add(c.claimant_id)
        if c.approver_id: user_ids.add(c.approver_id)

    users_map = {}
    if user_ids:
        result = await db.execute(select(UserModel).where(UserModel.id.in_(list(user_ids))))
        for u in result.scalars().all():
            user_data = {
                "name": u.full_name or "Unknown",
                "email": u.email or "",
                "employee_id": u.employee_id or "N/A",
                "department": "N/A"  # Department not in current schema
            }
            # Map by user ID
            users_map[str(u.id)] = user_data
            # Map by Employee ID
            if u.employee_id:
                users_map[str(u.employee_id)] = user_data

    # 4. Generate CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    # Header
    writer.writerow([
        "Employee ID", "Name", "Email", "Leave Type", 
        "Start Date", "End Date", "Deductible Days", "Status", "Approved By"
    ])

    # Rows
    for l in leaves:
        u = users_map.get(str(l.applicant_id), {})
        
        app_id_raw = l.approver_id
        app_id_key = str(app_id_raw) if app_id_raw else ""
        approver_data = users_map.get(app_id_key, {})
        
        if approver_data.get("name"):
            approver_name = approver_data["name"]
        else:
            # Fallback for deleted users or missing IDs
            approver_name = f"Unknown User ({app_id_raw})" if app_id_raw else ""
        
        writer.writerow([
            u.get("employee_id", ""),
            u.get("name", ""),
            u.get("email", ""),
            l.type.value if hasattr(l.type, 'value') else str(l.type),
            str(l.start_date),
            str(l.end_date) if l.end_date else "N/A",
            float(l.deductible_days),
            l.status.value if hasattr(l.status, 'value') else str(l.status),
            approver_name
        ])
        
    for c in comp_offs:
        u = users_map.get(str(c.claimant_id), {})
        
        app_id_raw = c.approver_id
        app_id_key = str(app_id_raw) if app_id_raw else ""
        approver_data = users_map.get(app_id_key, {})
        
        if approver_data.get("name"):
            approver_name = approver_data["name"]
        else:
             # Fallback for deleted users or missing IDs
            approver_name = f"Unknown User ({app_id_raw})" if app_id_raw else ""
        
        writer.writerow([
            u.get("employee_id", ""),
            u.get("name", ""),
            u.get("email", ""),
            "COMP_OFF_GRANT",
            str(c.work_date),
            str(c.work_date),
            "0 (Accrual)", # It's an accrual, not usage
            c.status.value if hasattr(c.status, 'value') else str(c.status),
            approver_name
        ])

    output.seek(0)
    
    return StreamingResponse(
        io.StringIO(output.getvalue()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=leave_report_{start_date}_{end_date}.csv"}
    )
