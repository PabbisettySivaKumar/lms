# LMS API Endpoints & Database Tables

## API Endpoints (by router)

Base URL is typically `http://localhost:8000` (or your server). All routes are registered and available when the app runs.

---

### Root
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check – "Leave Management System API is running" |

---

### Authentication (`/auth`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/login` | Login (returns JWT, reset_required, scope) |
| PATCH | `/auth/first-login-reset` | First-login password reset |
| POST | `/auth/forgot-password` | Request password reset email |
| POST | `/auth/reset-password` | Reset password with token |
| POST | `/auth/change-password` | Change password (authenticated) |

---

### Users (no prefix)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/users/me` | Current user profile |
| PATCH | `/users/me` | Update current user profile |
| POST | `/users/me/profile-picture` | Upload profile picture |
| POST | `/users/me/documents` | Upload user document |
| DELETE | `/users/me/documents/{filename}` | Delete user document |
| GET | `/admin/users` | List users (admin/HR/founder/co-founder) |
| POST | `/admin/users` | Create user (admin/HR/founder/co-founder) |
| PATCH | `/admin/users/{user_id}` | Update user |
| DELETE | `/admin/users/{user_id}` | Soft-delete user |
| PATCH | `/admin/users/{user_id}/balance` | Update user leave balance |
| GET | `/admin/managers` | List managers (for dropdown) |
| POST | `/admin/trigger-accrual` | Trigger accrual job (admin) |
| POST | `/admin/bootstrap` | Create DB + seed roles/admin (first-time) |
| POST | `/admin/backfill-staff-roles` | Backfill staff_roles table |
| GET | `/admin/integrity-check` | Integrity check (admin) |

---

### Manager (`/manager`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/manager/team` | Team list (HR/admin/founder see all; manager sees reports) |
| GET | `/manager/team/presence` | Team presence |

---

### Leaves (`/leaves`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/leaves/apply` | Apply for leave |
| POST | `/leaves/claim-comp-off` | Claim comp-off |
| PATCH | `/leaves/action/{item_id}` | Approve/reject leave or comp-off |
| POST | `/leaves/{leave_id}/cancel` | Cancel leave (or request cancellation) |
| GET | `/leaves/pending` | Pending leaves (for approvers) |
| GET | `/leaves/mine` | Current user's leaves |
| GET | `/leaves/export/stats` | Export leave stats |
| GET | `/leaves/export` | Export leave data |

---

### Holidays
| Method | Path | Description |
|--------|------|-------------|
| POST | `/admin/holidays/bulk` | Bulk create holidays |
| POST | `/admin/holidays` | Create single holiday |
| DELETE | `/admin/holidays/{holiday_id}` | Delete holiday |
| POST | `/admin/yearly-reset` | Trigger yearly reset job |
| GET | `/calendar/holidays` | List holidays (calendar) |

---

### Policies (`/policies`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/policies/active` | Active policy for current year |
| GET | `/policies` | List all (non–soft-deleted) policies |
| GET | `/policies/documents-by-year` | Documents grouped by year (incl. deleted-quota years) |
| POST | `/policies` | Create or update policy (quotas) |
| POST | `/policies/{year}/document` | Upload policy document |
| DELETE | `/policies/{year}/document` | Delete policy document (query `?url=...`) |
| DELETE | `/policies/{year}` | Soft-delete policy (keep documents) |
| POST | `/policies/{year}/acknowledge` | Acknowledge document (query `?document_url=...`) |
| GET | `/policies/{year}/my-acknowledgments` | Current user's acknowledgments for year |
| GET | `/policies/{year}/report` | Acknowledgment report for year |

---

### Static
| Method | Path | Description |
|--------|------|-------------|
| GET | `/static/*` | Static files (uploads, etc.) |

---

## Database Tables

All tables are defined in SQLAlchemy models and created by `init_db()` (or migrations). Tables in use:

| Table | Model / Module | Purpose |
|-------|----------------|---------|
| `users` | user.py (User) | Core user accounts |
| `user_profiles` | user_profile.py | Profile (DOB, address, family, etc.) |
| `user_documents` | user.py (UserDocument) | User-uploaded documents |
| `roles` | role.py (Role) | Role definitions (employee, manager, hr, …) |
| `role_scopes` | role.py (RoleScope) | Role–scope mapping |
| `user_roles` | role.py (UserRole) | User–role assignment |
| `staff_roles` | staff_role.py | Staff role (founder, co_founder, hr, manager, admin) |
| `user_leave_balances` | balance.py (UserLeaveBalance) | Leave balances per type |
| `user_balance_history` | balance.py (UserBalanceHistory) | Balance change history |
| `leave_requests` | leave.py (LeaveRequestModel) | Leave applications |
| `comp_off_claims` | leave.py (CompOffClaimModel) | Comp-off claims |
| `leave_comments` | leave.py (LeaveComment) | Comments on leave |
| `leave_attachments` | leave.py (LeaveAttachment) | Attachments on leave |
| `policies` | policy.py (Policy) | Yearly policy (quotas, is_active, is_deleted) |
| `policy_documents` | policy.py (PolicyDocument) | Policy PDFs/files |
| `policy_acknowledgments` | policy.py (PolicyAcknowledgment) | User acknowledgments per document/year |
| `holidays` | holiday.py | Holiday calendar |
| `audit_logs` | audit.py | Audit trail |
| `notifications` | notification.py | Notifications |
| `job_logs` | job.py | Scheduler/job logs |

---

## Summary

- **Endpoints:** All routes above are registered in `main.py` via `app.include_router(...)` for auth, users, manager, leaves, holidays, calendar, and policies. They are running when the FastAPI app is up.
- **Tables:** The 20 tables listed are the ones used by the app; they are created by `init_db()` (and/or Alembic migrations if you use them).
