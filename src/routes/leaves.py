import os
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from datetime import date, timedelta
from typing import List, Union, Optional
from bson import ObjectId

from src.db import db, users_collection
from src.models.leave import (
    LeaveRequestCreate, LeaveStatus, LeaveType, 
    CompOffClaimCreate, CompOffStatus
)
from src.models.user import UserRole, User
from src.routes.auth import get_current_user_email
from src.services.email import send_email

router = APIRouter(prefix="/leaves", tags=["Leaves"])
leaves_collection = db["leave_requests"]
comp_off_collection = db["comp_off_claims"]
holidays_collection = db["holidays"]

async def get_current_user(email: str = Depends(get_current_user_email)):
    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user["_id"] = str(user["_id"])
    return User(**user)

async def calculate_deductible_days(start_date: date, end_date: date) -> float:
    deductible = 0.0
    current = start_date
    while current <= end_date:
        # Check if weekend (Sat=5, Sun=6)
        if current.weekday() in [5, 6]:
            current += timedelta(days=1)
            continue
            
        # Check if holiday
        is_holiday = await holidays_collection.find_one({"date": str(current)})
        if is_holiday:
            current += timedelta(days=1)
            continue
            
        deductible += 1.0
        current += timedelta(days=1)
        
    return deductible

@router.post("/apply", response_model=dict)
async def apply_leave(leave: LeaveRequestCreate, user: User = Depends(get_current_user)):
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

    # 2. Overlap Check
    # Complex because of Sabbatical (potential None/Open-ended)
    # We need to find if ANY existing leave overlaps with [new_start, new_end]
    
    # Query construction
    query_conditions = [
        {"applicant_id": user.id},
        {"status": {"$in": [LeaveStatus.PENDING, LeaveStatus.APPROVED]}}
    ]

    # New Request Range: A=[start, end] (end might be infinity/None)
    new_start = str(leave.start_date)
    new_end = str(leave.end_date) if leave.end_date else None

    # We iterate and check manually or build complex OR query?
    # Mongo query for overlap: StartA <= EndB AND EndA >= StartB
    # But End might be null.
    
    # Let's simple fetch all active leaves for user and check in python for complex 'None' logic
    active_leaves = leaves_collection.find({
        "applicant_id": user.id,
        "status": {"$in": [LeaveStatus.PENDING, LeaveStatus.APPROVED]}
    })
    
    async for l in active_leaves:
        existing_start = l["start_date"]
        existing_end = l.get("end_date") # Might be None for Sabbatical
        
        # Check Overlap
        # Two infinite ranges always overlap if starts match or ... logic
        
        # Case 1: Both defined
        if new_end and existing_end:
            if existing_start <= new_end and existing_end >= new_start:
                raise HTTPException(status_code=400, detail=f"Overlaps with existing leave ({existing_start} to {existing_end})")
        
        # Case 2: Existing is Sabbatical (Infinite End)
        elif not existing_end:
            # Overlaps if New End >= Existing Start (which is always true basically if new is future?)
            # or simply New Start >= Existing Start (sabbatical active)
            # Actually if Sabbatical started Jan 1, and I request Jan 5... overlap.
            # If I request leave BEFORE Sabbatical? 
            if new_end:
                 if new_end >= existing_start: # Overlap
                      raise HTTPException(status_code=400, detail="Overlaps with ongoing Sabbatical")
            else:
                 # Both infinite... surely overlap unless dates extremely far apart? (Unlikely)
                 raise HTTPException(status_code=400, detail="Overlaps with ongoing Sabbatical")

        # Case 3: New is Sabbatical (Infinite End)
        elif not new_end:
            # Overlaps if Existing End >= New Start
            if existing_end >= new_start:
                 raise HTTPException(status_code=400, detail=f"Sabbatical overlaps with existing leave ({existing_start} to {existing_end})")
        
        
    # 3. Balance & Deductible Calculation
    deductible_days = 0.0
    
    if leave.type in [LeaveType.CASUAL, LeaveType.SICK, LeaveType.EARNED, LeaveType.COMP_OFF]:
        deductible_days = await calculate_deductible_days(leave.start_date, leave.end_date)
        
        # Balance Check
        if leave.type == LeaveType.COMP_OFF:
            if user.comp_off_balance < deductible_days:
                raise HTTPException(status_code=400, detail="Insufficient Comp-Off balance")
        elif leave.type == LeaveType.CASUAL:
            if user.casual_balance < deductible_days:
                raise HTTPException(status_code=400, detail="Insufficient Casual Leave balance")
        elif leave.type == LeaveType.SICK:
            if user.sick_balance < deductible_days:
                raise HTTPException(status_code=400, detail="Insufficient Sick Leave balance")
        elif leave.type == LeaveType.EARNED:
            if user.earned_balance < deductible_days:
                raise HTTPException(status_code=400, detail="Insufficient Earned Leave balance")
    
    # Maternity / Sabbatical = 0 deductible (or handled purely as status without balance)
    # User said "Ensure maternity does not deduct from standard CL/SL".
    
    
    # DETERMINE APPROVER
    approver_id = user.manager_id
    approver_email = None
    
    # Use user's manager if exists
    if approver_id:
        manager = await users_collection.find_one({"employee_id": approver_id})
        if manager:
            approver_email = manager["email"]
            
    # Fallback to HR if no manager assigned
    if not approver_id:
        hr_user = await users_collection.find_one({"role": UserRole.HR})
        if hr_user:
            approver_id = hr_user["employee_id"]
            approver_email = hr_user["email"]
    
    # Save to DB
    leave_dict = leave.dict()
    leave_dict["applicant_id"] = user.id
    leave_dict["status"] = LeaveStatus.PENDING
    leave_dict["deductible_days"] = deductible_days
    leave_dict["approver_id"] = approver_id
    leave_dict["start_date"] = str(leave.start_date)
    leave_dict["end_date"] = str(leave.end_date) if leave.end_date else None
    
    res = await leaves_collection.insert_one(leave_dict)
    
    # NOTIFICATION
    if approver_email:
        frontend_url = "http://localhost:3000" # Default or env 
        # In a real app we'd get this from os.getenv("FRONTEND_URL")
        
        dates_str = f"{leave.start_date}"
        if leave.end_date:
             dates_str += f" to {leave.end_date}"
        
        # Leave Type Formatting
        leave_type_map = {
            "CASUAL": "Casual Leave",
            "SICK": "Sick Leave",
            "EARNED": "Earned Leave",
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

        await send_email(
            to_email=approver_email, 
            subject=f"New Leave Request from {user.full_name}",
            body=email_body,
            subtype="html"
        )
        
    return {
        "message": "Leave application submitted", 
        "id": str(res.inserted_id), 
        "deductible_days": deductible_days,
        "assigned_approver": approver_id
    }

@router.post("/claim-comp-off", response_model=dict)
async def claim_comp_off(claim: CompOffClaimCreate, user: User = Depends(get_current_user)):
    if claim.work_date > date.today():
        raise HTTPException(status_code=400, detail="Cannot claim comp-off for future dates")
    
    # Determine Approver (Same logic: Manager -> HR)
    approver_id = user.manager_id
    approver_email = None
    
    if approver_id:
        manager = await users_collection.find_one({"employee_id": approver_id})
        if manager:
            approver_email = manager["email"]
    
    if not approver_id:
        hr_user = await users_collection.find_one({"role": UserRole.HR})
        if hr_user:
            approver_id = hr_user["employee_id"]
            approver_email = hr_user["email"]

    claim_dict = claim.dict()
    claim_dict["claimant_id"] = user.id
    claim_dict["status"] = CompOffStatus.PENDING
    claim_dict["work_date"] = str(claim.work_date)
    claim_dict["approver_id"] = approver_id
    
    res = await comp_off_collection.insert_one(claim_dict)
    
    # NOTIFICATION
    if approver_email:
        await send_email(
            to_email=approver_email,
            subject=f"New Comp-Off Claim from {user.full_name}",
            body=f"Work Date: {claim.work_date}\nReason: {claim.reason}"
        )
    
    return {"message": "Comp-off claim submitted", "id": str(res.inserted_id), "assigned_approver": approver_id}

@router.patch("/action/{item_id}")
async def action_leave(
    item_id: str, 
    action: str, # APPROVE or REJECT
    note: str = None,
    background_tasks: BackgroundTasks = None,
    approver: User = Depends(get_current_user)
):
    if action not in ["APPROVE", "REJECT"]:
        raise HTTPException(status_code=400, detail="Invalid action")
        
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    # Try finding in Leave Requests first
    item_type = "leave"
    item = await leaves_collection.find_one({"_id": ObjectId(item_id)})
    
    # If not found, try Comp-Off Claims
    if not item:
        item_type = "comp_off"
        item = await comp_off_collection.find_one({"_id": ObjectId(item_id)})
        
    if not item:
        raise HTTPException(status_code=404, detail="Request not found")
        
    current_status = item["status"]
    if current_status != "Pending": # PENDING in enum is usually 'Pending' or 'pending', check Enum definition. 
        # Assuming Enum values are capitalized or we check equality directly. 
        # If stored as string "Pending", check that.
        # Let's check safely against both possible Enum string values if we aren't sure, 
        # or stick to the Enums imported.
        if current_status not in [LeaveStatus.PENDING, CompOffStatus.PENDING, LeaveStatus.CANCELLATION_REQUESTED]:
             raise HTTPException(status_code=400, detail="Request is not pending or cancellation requested")

    # STRICT PERMISSION CHECK
    # Rule 1: Assigned Manager
    is_assigned_manager = (item.get("approver_id") == approver.employee_id)
    
    # Rule 2: God Mode (Admin, Founder, HR)
    is_super_approver = approver.role in [UserRole.ADMIN, UserRole.FOUNDER, UserRole.HR]
    
    if not (is_assigned_manager or is_super_approver):
         raise HTTPException(status_code=403, detail="You are not authorized to approve this request")

    # EXECUTE ACTION
    if item_type == "leave":
        new_status = LeaveStatus.APPROVED if action == "APPROVE" else LeaveStatus.REJECTED
        
        # Handle Cancellation Approval
        if current_status == LeaveStatus.CANCELLATION_REQUESTED:
             if action == "APPROVE":
                 new_status = LeaveStatus.CANCELLED
             else:
                 # Rejecting cancellation means it goes back to APPROVED? or stays CANCELLATION_REQUESTED?
                 # Usually reverts to APPROVED (request denied).
                 new_status = LeaveStatus.APPROVED
                 
        applicant_id = item["applicant_id"]
        
        # LOGIC:
        # 1. PENDING -> APPROVED: Deduct
        # 2. CANCELLATION_REQUESTED -> CANCELLED: Refund
        
        if current_status == LeaveStatus.PENDING and new_status == LeaveStatus.APPROVED:
            # Deduct balance
            applicant = await users_collection.find_one({"_id": ObjectId(applicant_id)})
            deductible = item["deductible_days"]
            leave_type = item["type"]
            
            update_field = None
            if leave_type == LeaveType.COMP_OFF:
                update_field = "comp_off_balance"
            elif leave_type == LeaveType.CASUAL:
                update_field = "casual_balance"
            elif leave_type == LeaveType.SICK:
                update_field = "sick_balance"
            elif leave_type == LeaveType.EARNED:
                update_field = "earned_balance"
                
            if update_field:
                if applicant.get(update_field, 0.0) < deductible:
                     raise HTTPException(status_code=400, detail="Insufficient balance at approval time")
                
                await users_collection.update_one(
                    {"_id": ObjectId(applicant_id)},
                    {"$inc": {update_field: -deductible}}
                )
                
        elif current_status == LeaveStatus.CANCELLATION_REQUESTED and new_status == LeaveStatus.CANCELLED:
             # Refund balance
            applicant = await users_collection.find_one({"_id": ObjectId(applicant_id)})
            deductible = item["deductible_days"]
            leave_type = item["type"]
            
            update_field = None
            if leave_type == LeaveType.COMP_OFF:
                update_field = "comp_off_balance"
            elif leave_type == LeaveType.CASUAL:
                update_field = "casual_balance"
            elif leave_type == LeaveType.SICK:
                update_field = "sick_balance"
            elif leave_type == LeaveType.EARNED:
                update_field = "earned_balance"
            
            if update_field:
                await users_collection.update_one(
                    {"_id": ObjectId(applicant_id)},
                    {"$inc": {update_field: deductible}} # Add back
                )
        
        await leaves_collection.update_one(
            {"_id": ObjectId(item_id)},
            {"$set": {"status": new_status, "approver_id": str(approver.id), "manager_note": note}}
        )
        
    else: # comp_off
        new_status = CompOffStatus.APPROVED if action == "APPROVE" else CompOffStatus.REJECTED
        applicant_id = item["claimant_id"]
        
        if new_status == CompOffStatus.APPROVED:
            # Increment comp-off balance
            await users_collection.update_one(
                {"_id": ObjectId(applicant_id)},
                {"$inc": {"comp_off_balance": 1.0}}
            )
            
        await comp_off_collection.update_one(
            {"_id": ObjectId(item_id)},
            {"$set": {"status": new_status, "approver_id": str(approver.id), "manager_note": note}}
        )

    # NOTIFICATION
    applicant = await users_collection.find_one({"_id": ObjectId(applicant_id)})
    if applicant and applicant.get("email"):
        status_color = "#16a34a" if action == "APPROVE" else "#dc2626"
        action_text = "APPROVED" if action == "APPROVE" else "REJECTED"
        
        email_body = f"""
        <html>
            <body>
                <p>Hello {applicant['full_name']},</p>
                <p>Your leave request has been <strong style="color: {status_color};">{action_text}</strong> by {approver.full_name}.</p>
                
                <p><strong>Manager's Note:</strong><br>
                <em>{note or 'None'}</em></p>
                
                <p>You can view your leave status at:</p>
                <p>
                    <a href="{frontend_url}/dashboard/my-leaves" 
                    style="color: #2563EB; text-decoration: underline; font-weight: bold;">
                    View My Leaves
                    </a>
                </p>
                
                <p>Thanks,<br>
                LMS Team</p>
            </body>
        </html>
        """

        if background_tasks:
            background_tasks.add_task(
                send_email,
                to_email=applicant["email"],
                subject=f"Leave Request {action_text}", 
                body=email_body,
                subtype="html"
            )
        else:
            # Fallback for sync testing
            await send_email(
                to_email=applicant["email"],
                subject=f"Leave Request {action_text}", 
                body=email_body,
                subtype="html"
            )

    return {"message": f"Request {new_status}"}

@router.post("/{leave_id}/cancel")
async def cancel_leave(leave_id: str, user: User = Depends(get_current_user)):
    # Find the leave
    leave = await leaves_collection.find_one({
        "_id": ObjectId(leave_id),
        "applicant_id": user.id
    })
    
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")
        
    current_status = leave["status"]
    
    # Case A: Pending -> Delete & Refund (if applicable - actually PENDING didn't deduct yet in current logic? 
    # WAIT: allow me to check apply_leave logic. 
    # In apply_leave: "deductible_days" is calculated but balance is NOT deducted. 
    # Balance is deducted in action_leave when APPROVED.
    # So for PENDING, we just delete or mark cancelled. No refund needed really, but let's be safe.
    
    if current_status == LeaveStatus.PENDING:
        # Just update status to CANCELLED or delete? User asked to "Delete or mark as Withdrawn".
        # Let's mark as CANCELLED to keep history.
        await leaves_collection.update_one(
            {"_id": ObjectId(leave_id)},
            {"$set": {"status": LeaveStatus.CANCELLED}}
        )
        return {"message": "Leave withdrawn successfully."}
        
    # Case B: Approved -> Immediate Cancel + Refund
    elif current_status == LeaveStatus.APPROVED:
        # Refund Policy: Allow immediate self-cancellation
        
        # 1. Calculate refund days
        deductible = leave.get("deductible_days", 0.0)
        leave_type = leave.get("type")
        
        # 2. Refund Balance
        update_field = None
        if leave_type == LeaveType.COMP_OFF:
            update_field = "comp_off_balance"
        elif leave_type == LeaveType.CASUAL:
            update_field = "casual_balance"
        elif leave_type == LeaveType.SICK:
            update_field = "sick_balance"
        elif leave_type == LeaveType.EARNED:
            update_field = "earned_balance"
        
        # Only refund if it was a deductible type (Maternity/Sabbatical are 0 anyway)
        if update_field and deductible > 0:
             await users_collection.update_one(
                {"_id": ObjectId(user.id)},
                {"$inc": {update_field: deductible}}
            )

        # 3. Update Status
        await leaves_collection.update_one(
            {"_id": ObjectId(leave_id)},
            {"$set": {"status": LeaveStatus.CANCELLED}}
        )
        
        return {"message": "Leave cancelled and balance refunded."}
        
    # Case C: Rejected or already Cancelled
    else:
        raise HTTPException(status_code=400, detail="Cannot cancel this leave.")

@router.get("/pending", response_model=dict)
async def get_pending_requests(user: User = Depends(get_current_user)):
    # If user is Admin/HR, they can see ALL pending requests (Optional, or strict?)
    # User's request: "Return requests where approver_id == current_user.id OR user is Admin/HR"
    
    query = {"status": {"$in": ["Pending", "pending"]}} # robust check? Use Enums ideally
    # Actually let's use the Enums from the models.
    # But wait, Enums might be different strings. 'Pending' vs 'pending'.
    # In apply_leave we set LeaveStatus.PENDING. Let's assume consistent usage.
    
    filter_query = {
        "$or": [
            {"status": LeaveStatus.PENDING},
            {"status": CompOffStatus.PENDING}
        ]
    }
    
    # Filter by approver if not God Mode
    if user.role not in [UserRole.ADMIN, UserRole.HR, UserRole.FOUNDER]:
        # Strict: only what is assigned to me
        filter_query["approver_id"] = user.employee_id
    else:
        # God mode: can see everything, OR specific assignments?
        # Typically they want to see everything to clear backlogs.
        pass

    # Fetch Leaves
    pending_leaves = []
    leave_cursor = leaves_collection.find(filter_query) # Note: Leave collection might not have CompOffStatus if they differ
    # We need separate queries because fields might differ / collections differ
    
    # LEAVES QUERY
    l_query = {"status": LeaveStatus.PENDING}
    if user.role not in [UserRole.ADMIN, UserRole.HR, UserRole.FOUNDER]:
        l_query["approver_id"] = user.employee_id
        
    leaves = []
    async for doc in leaves_collection.find(l_query):
        doc["_id"] = str(doc["_id"])
        leaves.append(doc)
        
    # COMP OFF QUERY
    c_query = {"status": CompOffStatus.PENDING}
    if user.role not in [UserRole.ADMIN, UserRole.HR, UserRole.FOUNDER]:
        c_query["approver_id"] = user.employee_id
        
    comp_offs = []
    async for doc in comp_off_collection.find(c_query):
        doc["_id"] = str(doc["_id"])
        comp_offs.append(doc)
        
    # Fetch Applicant Details
    applicant_ids = set()
    for l in leaves:
        applicant_ids.add(l["applicant_id"])
    for c in comp_offs:
        applicant_ids.add(c["claimant_id"])
        
    users_map = {}
    if applicant_ids:
        # Convert string IDs back to ObjectId if stored as ObjectId in users, 
        # or string if stored as string. User model usually has ObjectId _id.
        # Check get_current_user: user["_id"] = str(user["_id"]). 
        # So IDs in leaves are likely strings.
        # But querying _id in users collection requires ObjectId usually.
        obj_ids = [ObjectId(uid) for uid in applicant_ids]
        async for u in users_collection.find({"_id": {"$in": obj_ids}}):
             users_map[str(u["_id"])] = u["full_name"]

    # Attach Names
    for l in leaves:
        l["applicant_name"] = users_map.get(l["applicant_id"], "Unknown")
        l["id"] = l["_id"] # alias for frontend convenience
        
    for c in comp_offs:
        c["applicant_name"] = users_map.get(c["claimant_id"], "Unknown")
        c["type"] = "COMP_OFF_GRANT" # Distinct from leave type COMP_OFF
        c["start_date"] = c["work_date"] # Normalize date for table
        c["end_date"] = c["work_date"]
        c["deductible_days"] = 1.0 # Earning 1 day
        c["id"] = c["_id"]

    return {
        "leaves": leaves,
        "comp_offs": comp_offs
    }

@router.get("/mine", response_model=List[dict])
async def get_my_leaves(user: User = Depends(get_current_user)):
    # 1. Fetch Leaves
    leaves = []
    async for doc in leaves_collection.find({"applicant_id": user.id}):
        doc["_id"] = str(doc["_id"])
        # Format for consistency
        leaves.append({
            "id": doc["_id"],
            "start_date": doc["start_date"],
            "end_date": doc["end_date"],
            "type": doc["type"],
            "status": doc["status"].upper(), # Normalize status to uppercase
            "deductible_days": doc.get("deductible_days", 0)
        })

    # 2. Fetch Comp-Offs
    async for doc in comp_off_collection.find({"claimant_id": user.id}):
        doc["_id"] = str(doc["_id"])
        leaves.append({
            "id": doc["_id"],
            "start_date": doc["work_date"],
            "end_date": doc["work_date"], # Same day
            "type": "COMP_OFF",
            "status": doc["status"].upper(),
            "deductible_days": 1.0 # Earning 1 day, effectively
        })

    return leaves
