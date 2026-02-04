import logging
from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Response, Request
import shutil
import os
from pathlib import Path
from backend.db import get_db, AsyncSessionLocal
from backend.models import (
    Policy, PolicyDocument as PolicyDocumentModel, PolicyAcknowledgment,
    User as UserModel, UserRole as UserRoleModel, Role
)
from sqlalchemy import select, and_, func  # type: ignore
from sqlalchemy.orm import selectinload  # type: ignore
from backend.models.policy import LeavePolicy, PolicyDocumentSchema as PolicyDocument, DocumentsByYearItem
from backend.routes.users import get_current_user, user_model_to_pydantic
from backend.routes.auth import get_current_user_email
from backend.models.user import UserSchema as User, UserRole
from typing import List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession  # type: ignore
from backend.utils.id_utils import to_int_id
from backend.services.audit import log_action as audit_log_action
from backend.utils.action_log import log_user_action

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/policies", tags=["Policies"])

# Helper to get current user with error handling (converts 401 to 403)
async def get_current_user_safe(email: str = Depends(get_current_user_email), db: AsyncSession = Depends(get_db)):
    """Get current user, converting any 401 errors to 403 to prevent logout."""
    try:
        # Directly query the user and convert to schema (same logic as get_current_user)
        result = await db.execute(
            select(UserModel).where(UserModel.email == email).options(selectinload(UserModel.profile))
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not found"
            )
        # Use the user_model_to_pydantic function to get the full user schema
        return await user_model_to_pydantic(user, db)
    except HTTPException as e:
        # Convert 401 to 403 to prevent automatic logout
        if e.status_code == status.HTTP_401_UNAUTHORIZED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=e.detail or "Authentication failed"
            )
        raise
    except Exception as e:
        logger.exception("Error in get_current_user_safe: %s", e)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication failed"
        )

# Helper to verify admin
async def verify_admin(current_user: User = Depends(get_current_user_safe), db: AsyncSession = Depends(get_db)):
    """Verify user has admin/HR/founder role by querying user_roles table."""
    try:
        # Ensure we have a valid user object
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not authenticated"
            )
        
        user_id = current_user.id
        # Check for None specifically (not just falsy, since 0 could be a valid ID)
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User ID not found"
            )
        
        # Convert user_id to integer if it's a string
        
        user_id_int = to_int_id(user_id)
        if user_id_int is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid user ID"
            )
        
        # Get user's role from user_roles table using SQLAlchemy
        result = await db.execute(
            select(UserRoleModel, Role)
            .join(Role, UserRoleModel.role_id == Role.id)
            .where(and_(UserRoleModel.user_id == user_id_int, UserRoleModel.is_active == True))
        )
        user_role_record = result.first()
        
        if not user_role_record:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No active role found for user"
            )
        
        # When selecting multiple models, result.first() returns a tuple
        user_role_name = user_role_record[1].name  # user_role_record[0] is UserRoleModel, [1] is Role
        allowed_roles = [UserRole.ADMIN.value.lower(), UserRole.FOUNDER.value.lower(), UserRole.CO_FOUNDER.value.lower(), UserRole.HR.value.lower()]
        if user_role_name.lower() not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required role: admin, hr, founder, or co-founder. Current role: {user_role_name}"
            )
        
        return current_user
    except HTTPException as http_exc:
        # Re-raise HTTPExceptions as-is (they already have proper status codes)
        # But ensure we never return 401 from here (only 403)
        if http_exc.status_code == status.HTTP_401_UNAUTHORIZED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Authentication required"
            )
        raise
    except Exception as e:
        logger.exception("Error in verify_admin: %s", e)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Authorization check failed: {str(e)}"
        )

@router.get("/active", response_model=LeavePolicy)
async def get_active_policy(response: Response, db: AsyncSession = Depends(get_db)):
    """
    Get active policy with HTTP caching.
    """
    current_year = datetime.now().year
    
    # Try to find policy for current year (exclude soft-deleted)
    result = await db.execute(
        select(Policy).where(
            and_(Policy.year == current_year, Policy.is_deleted == False)
        )
    )
    policy = result.scalar_one_or_none()
    
    if policy:
        # Fetch documents for this policy
        documents_result = await db.execute(
            select(PolicyDocumentModel).where(PolicyDocumentModel.policy_id == policy.id)
        )
        documents_list = documents_result.scalars().all()
        documents = [
            PolicyDocument(
                id=doc.id,
                policy_id=doc.policy_id,
                name=doc.name,
                url=doc.url,
                uploaded_at=doc.uploaded_at
            )
            for doc in documents_list
        ]
        
        logger.debug("Active policy year=%s: %s documents", policy.year, len(documents))
        # Set cache headers (shorter cache time to allow fresh data after uploads)
        response.headers["Cache-Control"] = "public, max-age=60, must-revalidate"
        return LeavePolicy(
            id=policy.id,
            year=policy.year,
            casual_leave_quota=policy.casual_leave_quota,
            sick_leave_quota=policy.sick_leave_quota,
            wfh_quota=policy.wfh_quota,
            is_active=policy.is_active,
            documents=documents,
            created_at=policy.created_at,
            updated_at=policy.updated_at
        )
        
    # Fallback to default policy if none found
    default_policy = {
        "year": current_year,
        "casual_leave_quota": 12,
        "sick_leave_quota": 3,
        "wfh_quota": 2,
        "is_active": True
    }
    # Set cache headers for default policy too
    response.headers["Cache-Control"] = "public, max-age=1800"
    return LeavePolicy(**default_policy)

@router.get("", response_model=List[LeavePolicy])
#@router.get("/", response_model=List[LeavePolicy])
async def get_all_policies(
    response: Response,
    current_user: User = Depends(verify_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all policies with HTTP caching for static data. Excludes soft-deleted policies.
    """
    result = await db.execute(
        select(Policy).where(Policy.is_deleted == False).order_by(Policy.year.desc())
    )
    policies_models = result.scalars().all()
    
    policies = []
    for p in policies_models:
        # Fetch documents for this policy
        documents_result = await db.execute(
            select(PolicyDocumentModel).where(PolicyDocumentModel.policy_id == p.id)
        )
        documents_list = documents_result.scalars().all()
        # Convert documents to PolicyDocumentSchema objects
        documents = [
            PolicyDocument(
                id=doc.id,
                policy_id=doc.policy_id,
                name=doc.name,
                url=doc.url,
                uploaded_at=doc.uploaded_at
            )
            for doc in documents_list
        ]
        
        logger.debug("Policy year=%s: %s documents", p.year, len(documents))
        policies.append(LeavePolicy(
            id=p.id,
            year=p.year,
            casual_leave_quota=p.casual_leave_quota,
            sick_leave_quota=p.sick_leave_quota,
            wfh_quota=p.wfh_quota,
            is_active=p.is_active,
            documents=documents,
            created_at=p.created_at,
            updated_at=p.updated_at
        ))
    
    # Set cache headers (shorter cache time to allow fresh data after uploads)
    response.headers["Cache-Control"] = "public, max-age=60, must-revalidate"
    return policies


@router.get("/documents-by-year", response_model=List[DocumentsByYearItem])
async def get_documents_by_year(
    response: Response,
    current_user: User = Depends(verify_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Get documents grouped by year for all years that have at least one document.
    Includes years whose leave policy was soft-deleted, so Policy Documents UI can show them.
    """
    # All policy_ids that have at least one document
    result = await db.execute(
        select(PolicyDocumentModel.policy_id).distinct()
    )
    policy_ids = [row[0] for row in result.fetchall()]
    if not policy_ids:
        response.headers["Cache-Control"] = "public, max-age=60, must-revalidate"
        return []
    # Policies (including soft-deleted) for those ids, ordered by year desc
    result = await db.execute(
        select(Policy).where(Policy.id.in_(policy_ids)).order_by(Policy.year.desc())
    )
    policies = result.scalars().all()
    out: List[DocumentsByYearItem] = []
    for p in policies:
        doc_result = await db.execute(
            select(PolicyDocumentModel).where(PolicyDocumentModel.policy_id == p.id)
        )
        docs = doc_result.scalars().all()
        out.append(DocumentsByYearItem(
            year=p.year,
            documents=[
                PolicyDocument(id=doc.id, policy_id=doc.policy_id, name=doc.name, url=doc.url, uploaded_at=doc.uploaded_at)
                for doc in docs
            ],
        ))
    response.headers["Cache-Control"] = "public, max-age=60, must-revalidate"
    return out


@router.post("", response_model=LeavePolicy)
async def create_or_update_policy(
    request: Request,
    policy_data: LeavePolicy,
    current_user: User = Depends(verify_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        # Check if policy exists for the year (including soft-deleted, so we can restore)
        result = await db.execute(select(Policy).where(Policy.year == policy_data.year))
        existing = result.scalar_one_or_none()
        
        if existing:
            # Capture old values before update (for audit)
            old_values_policy = {
                "year": existing.year,
                "casual_leave_quota": existing.casual_leave_quota,
                "sick_leave_quota": existing.sick_leave_quota,
                "wfh_quota": existing.wfh_quota,
            }
            # Update existing policy (restore if it was soft-deleted)
            existing.casual_leave_quota = policy_data.casual_leave_quota
            existing.sick_leave_quota = policy_data.sick_leave_quota
            existing.wfh_quota = policy_data.wfh_quota
            existing.is_active = policy_data.is_active
            existing.is_deleted = False  # Restore if was soft-deleted; no-op otherwise
            await audit_log_action(
                db,
                "UPDATE_POLICY",
                "POLICY",
                user_id=current_user.id,
                affected_entity_id=existing.id,
                old_values=old_values_policy,
                new_values={"year": policy_data.year, "casual_leave_quota": policy_data.casual_leave_quota, "sick_leave_quota": policy_data.sick_leave_quota, "wfh_quota": policy_data.wfh_quota},
                actor_email=current_user.email,
                actor_employee_id=current_user.employee_id,
                actor_full_name=current_user.full_name,
                actor_role=getattr(current_user, "role", None),
                summary=f"{current_user.full_name} updated policy for year {policy_data.year}",
                request_method=request.method,
                request_path=request.url.path,
            )
            await db.commit()
            await db.refresh(existing)
            log_user_action(
                "UPDATE_POLICY",
                user_id=current_user.id,
                email=current_user.email,
                employee_id=current_user.employee_id,
                full_name=current_user.full_name,
                role=getattr(current_user, "role", None),
                year=policy_data.year,
            )
            updated = existing
        else:
            # Create new policy
            new_policy = Policy(
                year=policy_data.year,
                casual_leave_quota=policy_data.casual_leave_quota,
                sick_leave_quota=policy_data.sick_leave_quota,
                wfh_quota=policy_data.wfh_quota,
                is_active=policy_data.is_active,
            )
            db.add(new_policy)
            await db.flush()
            await audit_log_action(
                db,
                "CREATE_POLICY",
                "POLICY",
                user_id=current_user.id,
                affected_entity_id=new_policy.id,
                new_values={"year": policy_data.year, "casual_leave_quota": policy_data.casual_leave_quota, "sick_leave_quota": policy_data.sick_leave_quota, "wfh_quota": policy_data.wfh_quota},
                actor_email=current_user.email,
                actor_employee_id=current_user.employee_id,
                actor_full_name=current_user.full_name,
                actor_role=getattr(current_user, "role", None),
                summary=f"{current_user.full_name} created policy for year {policy_data.year}",
                request_method=request.method,
                request_path=request.url.path,
            )
            await db.commit()
            await db.refresh(new_policy)
            log_user_action(
                "CREATE_POLICY",
                user_id=current_user.id,
                email=current_user.email,
                employee_id=current_user.employee_id,
                full_name=current_user.full_name,
                role=getattr(current_user, "role", None),
                year=policy_data.year,
            )
            updated = new_policy
            
        if not updated:
            raise HTTPException(status_code=404, detail="Policy not found after save")
        
        # Fetch documents for this policy
        documents_result = await db.execute(
            select(PolicyDocumentModel).where(PolicyDocumentModel.policy_id == updated.id)
        )
        documents_list = documents_result.scalars().all()
        # Convert documents to PolicyDocumentSchema objects
        documents = [
            PolicyDocument(
                id=doc.id,
                policy_id=doc.policy_id,
                name=doc.name,
                url=doc.url,
                uploaded_at=doc.uploaded_at
            )
            for doc in documents_list
        ]
        
        return LeavePolicy(
            id=updated.id,
            year=updated.year,
            casual_leave_quota=updated.casual_leave_quota,
            sick_leave_quota=updated.sick_leave_quota,
            wfh_quota=updated.wfh_quota,
            is_active=updated.is_active,
            documents=documents,
            created_at=updated.created_at,
            updated_at=updated.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        error_detail = f"Failed to save policy: {str(e)}"
        logger.exception("Error in create_or_update_policy: %s", e)
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=error_detail
        )

@router.post("/{year}/document", response_model=LeavePolicy)
async def upload_policy_document(
    year: int, 
    name: Optional[str] = None,
    file: UploadFile = File(...), 
    current_user: User = Depends(verify_admin),
    db: AsyncSession = Depends(get_db)
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="File must have a filename")
    
    # If policy doesn't exist, create one with defaults
    result = await db.execute(select(Policy).where(Policy.year == year))
    policy = result.scalar_one_or_none()
    if not policy:
        default_policy = Policy(
            year=year,
            casual_leave_quota=12,
            sick_leave_quota=5,
            wfh_quota=2,
            is_active=True
        )
        db.add(default_policy)
        await db.flush()
        policy_id = default_policy.id
        await db.commit()
        await db.refresh(default_policy)
        policy = default_policy
        if not policy:
            raise HTTPException(status_code=500, detail="Failed to create policy")
    else:
        policy_id = policy.id
        if not policy_id:
            raise HTTPException(status_code=500, detail="Policy ID not found")
        
    UPLOAD_DIR = Path("static/uploads/policies")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    filename = f"{year}_{int(datetime.now().timestamp())}_{file.filename.replace(' ', '_')}"
    file_path = UPLOAD_DIR / filename
    
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()
        
    document_url = f"/static/uploads/policies/{filename}"
    doc_display_name = name if name else file.filename
    
    # Insert into policy_documents table
    new_document = PolicyDocumentModel(
        policy_id=policy_id,
        name=doc_display_name,
        url=document_url,
        uploaded_at=datetime.utcnow()
    )
    db.add(new_document)
    await db.commit()
    await db.refresh(policy)
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found after update")
    
    # Fetch documents for this policy
    documents_result = await db.execute(
        select(PolicyDocumentModel).where(PolicyDocumentModel.policy_id == policy.id)
    )
    documents_list = documents_result.scalars().all()
    # Convert documents to PolicyDocumentSchema objects
    documents = [
        PolicyDocument(
            id=doc.id,
            policy_id=doc.policy_id,
            name=doc.name,
            url=doc.url,
            uploaded_at=doc.uploaded_at
        )
        for doc in documents_list
    ]
    
    return LeavePolicy(
        id=policy.id,
        year=policy.year,
        casual_leave_quota=policy.casual_leave_quota,
        sick_leave_quota=policy.sick_leave_quota,
        wfh_quota=policy.wfh_quota,
        is_active=policy.is_active,
        documents=documents,
        created_at=policy.created_at,
        updated_at=policy.updated_at
    )

@router.delete("/{year}/document", response_model=LeavePolicy)
async def delete_policy_document(
    year: int, 
    url: str,
    current_user: User = Depends(verify_admin),
    db: AsyncSession = Depends(get_db)
):
    # Check if policy exists
    result = await db.execute(select(Policy).where(Policy.year == year))
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
        
    # Remove from disk
    # Extract filename from URL
    # URL: /static/uploads/policies/filename
    if "/static/uploads/policies/" in url:
        filename = url.split("/static/uploads/policies/")[1]
        file_path = Path("static/uploads/policies") / filename
        if file_path.exists():
            os.remove(file_path)
    
    # Remove from policy_documents table
    policy_id = policy.id
    if policy_id:
        result = await db.execute(
            select(PolicyDocumentModel).where(
                and_(PolicyDocumentModel.policy_id == policy_id, PolicyDocumentModel.url == url)
            )
        )
        document = result.scalar_one_or_none()
        if document:
            await db.delete(document)
    
    await db.commit()
    await db.refresh(policy)
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found after delete")
    
    # Fetch documents for this policy
    documents_result = await db.execute(
        select(PolicyDocumentModel).where(PolicyDocumentModel.policy_id == policy.id)
    )
    documents_list = documents_result.scalars().all()
    documents = [
        PolicyDocument(
            id=doc.id,
            policy_id=doc.policy_id,
            name=doc.name,
            url=doc.url,
            uploaded_at=doc.uploaded_at
        )
        for doc in documents_list
    ]
    
    return LeavePolicy(
        id=policy.id,
        year=policy.year,
        casual_leave_quota=policy.casual_leave_quota,
        sick_leave_quota=policy.sick_leave_quota,
        wfh_quota=policy.wfh_quota,
        is_active=policy.is_active,
        documents=documents,
        created_at=policy.created_at,
        updated_at=policy.updated_at
    )

@router.delete("/{year}")
async def delete_entire_policy(
    request: Request,
    year: int,
    current_user: User = Depends(verify_admin),
    db: AsyncSession = Depends(get_db),
):
    # Find policy (include soft-deleted so we can re-soft-delete if needed)
    result = await db.execute(select(Policy).where(Policy.year == year))
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    if getattr(policy, "is_deleted", False):
        raise HTTPException(status_code=404, detail="Policy already deleted")
    
    await audit_log_action(
        db,
        "DELETE_POLICY",
        "POLICY",
        user_id=current_user.id,
        affected_entity_id=policy.id,
        old_values={"year": year},
        actor_email=current_user.email,
        actor_employee_id=current_user.employee_id,
        actor_full_name=current_user.full_name,
        actor_role=getattr(current_user, "role", None),
        summary=f"{current_user.full_name} deleted policy for year {year}",
        request_method=request.method,
        request_path=request.url.path,
    )
    # Soft delete: mark policy as deleted and deactivate. Do NOT delete policy_documents or remove files.
    policy.is_deleted = True
    policy.is_active = False
    await db.commit()
    log_user_action(
        "DELETE_POLICY",
        user_id=current_user.id,
        email=current_user.email,
        employee_id=current_user.employee_id,
        full_name=current_user.full_name,
        role=getattr(current_user, "role", None),
        year=year,
    )
    return {"message": f"Policy for year {year} deleted successfully. Documents are kept."}

@router.post("/{year}/acknowledge")
async def acknowledge_policy(
    request: Request,
    year: int,
    document_url: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Check if policy exists for that year
    result = await db.execute(select(Policy).where(Policy.year == year))
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail=f"Policy for year {year} not found")

    # Save or update acknowledgment for this specific document
    user_id_int = current_user.id
    result = await db.execute(
        select(PolicyAcknowledgment).where(
            and_(
                PolicyAcknowledgment.user_id == user_id_int,
                PolicyAcknowledgment.year == year,
                PolicyAcknowledgment.document_url == document_url
            )
        )
    )
    existing_ack = result.scalar_one_or_none()
    
    if existing_ack:
        # Update existing acknowledgment
        existing_ack.acknowledged_at = datetime.utcnow()
    else:
        # Insert new acknowledgment
        new_ack = PolicyAcknowledgment(
            user_id=user_id_int,
            year=year,
            document_url=document_url,
            acknowledged_at=datetime.utcnow()
        )
        db.add(new_ack)

    await audit_log_action(
        db,
        "ACKNOWLEDGE_POLICY",
        "POLICY",
        user_id=current_user.id,
        affected_entity_id=policy.id,
        new_values={"year": year, "document_url": document_url},
        actor_email=current_user.email,
        actor_employee_id=current_user.employee_id,
        actor_full_name=current_user.full_name,
        actor_role=getattr(current_user, "role", None),
        summary=f"{current_user.full_name} acknowledged policy document for year {year}",
        request_method=request.method,
        request_path=request.url.path,
    )
    await db.commit()
    log_user_action(
        "ACKNOWLEDGE_POLICY",
        user_id=current_user.id,
        email=current_user.email,
        employee_id=current_user.employee_id,
        full_name=current_user.full_name,
        role=getattr(current_user, "role", None),
        year=year,
    )
    return {"message": "Document acknowledged successfully"}

@router.get("/{year}/my-acknowledgments")
async def get_my_acknowledgments(
    year: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(PolicyAcknowledgment).where(
            and_(
                PolicyAcknowledgment.user_id == current_user.id,
                PolicyAcknowledgment.year == year
            )
        )
    )
    acks_models = result.scalars().all()
    
    acks = []
    for a in acks_models:
        acks.append({
            "id": a.id,
            "_id": str(a.id),
            "user_id": str(a.user_id),
            "full_name": current_user.full_name,  # Get from current_user
            "email": current_user.email,  # Get from current_user
            "year": a.year,
            "document_url": a.document_url,
            "acknowledged_at": a.acknowledged_at.isoformat() if a.acknowledged_at else None
        })
    return acks

@router.get("/{year}/report")
async def get_acknowledgment_report(
    year: int,
    current_user: User = Depends(verify_admin),
    db: AsyncSession = Depends(get_db)
):
    # Get the policy to know total documents
    result = await db.execute(select(Policy).where(Policy.year == year))
    policy = result.scalar_one_or_none()
    
    # Count documents for this policy
    total_docs = 0
    if policy:
        result = await db.execute(
            select(func.count()).select_from(
                select(PolicyDocumentModel).where(PolicyDocumentModel.policy_id == policy.id).subquery()
            )
        )
        total_docs = result.scalar() or 0

    # Get all active employees
    result = await db.execute(select(UserModel).where(UserModel.is_active == True))
    users_models = result.scalars().all()
    
    # Get all acknowledgments for this year
    result = await db.execute(select(PolicyAcknowledgment).where(PolicyAcknowledgment.year == year))
    acks_models = result.scalars().all()
    
    # Group acknowledgments by user
    ack_map = {}
    for a in acks_models:
        uid = str(a.user_id)
        if uid not in ack_map:
            ack_map[uid] = []
        ack_map[uid].append(a)
    
    # Get user roles for each user
    report = []
    for user in users_models:
        user_id = str(user.id)
        user_acks = ack_map.get(user_id, [])
        acknowledged_count = len(user_acks)
        
        # Get user's role
        role_result = await db.execute(
            select(Role.name)
            .join(UserRoleModel, Role.id == UserRoleModel.role_id)
            .where(and_(UserRoleModel.user_id == user.id, UserRoleModel.is_active == True))
        )
        role_name = role_result.scalar_one_or_none()
        
        report.append({
            "user_id": user_id,
            "full_name": user.full_name,
            "email": user.email,
            "role": role_name or "N/A",
            "acknowledged_count": acknowledged_count,
            "total_documents": total_docs,
            "fully_acknowledged": acknowledged_count >= total_docs if total_docs > 0 else False,
            "acknowledgments": [
                {"document_url": a.document_url, "acknowledged_at": a.acknowledged_at.isoformat() if a.acknowledged_at else None}
                for a in user_acks
            ]
        })
    
    return report
