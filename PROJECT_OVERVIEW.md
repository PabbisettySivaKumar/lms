# Leave Management System — Project Overview

A detailed summary of what the system is, how it works, and how to run it.

---

## 1. What It Is

The **Leave Management System (LMS)** is a web application for companies to manage employee leave, holidays, and HR policies. Employees apply for leave and claim comp-off; managers approve or reject; admins configure policies, holidays, and user accounts. All balance changes and important actions are recorded in an audit trail and balance history.

### Tech Stack

| Layer | Technologies |
|-------|--------------|
| **Backend** | Python 3.10+, FastAPI, SQLAlchemy (async), Pydantic, PyMySQL |
| **Frontend** | Next.js, React, TypeScript, Tailwind CSS, Shadcn UI, React Query, Axios |
| **Database** | MySQL |
| **Auth** | JWT (HS256), role-based OAuth2-style scopes |
| **Email** | SMTP (e.g. Office 365) or optional Microsoft Graph API |
| **Migrations** | Alembic (optional for first deploy; bootstrap creates tables) |

### Key Backend Layout

- **`backend/main.py`** — FastAPI app, lifespan (DB init, scheduler), CORS, request logging, router includes.
- **`backend/routes/`** — `auth`, `users`, `manager`, `leaves`, `holidays`, `policies`.
- **`backend/models/`** — SQLAlchemy models (User, UserProfile, LeaveRequest, Policy, Holiday, etc.) and enums.
- **`backend/services/`** — `seed` (roles + admin), `email`, `email_graph`, `scheduler`, `balance_history`, `audit`.
- **`backend/utils/`** — `scopes`, `security`, `leave_utils`, `id_utils`, logging, request info.

### Key Frontend Layout

- **`frontend/src/app/`** — Next.js App Router: `(auth)/` (login, forgot-password, reset-password, force-reset), `dashboard/` (home, profile, settings, team, admin/*, employee/*).
- **`frontend/src/components/`** — `admin/` (user/holiday dialogs), `dashboard/` (apply leave, comp-off, calendar), `profile/`, `layout/` (Sidebar), `ui/` (Shadcn).
- **`frontend/src/lib/`** — API client, auth helpers, axios instance, error handling.
- **`frontend/src/hooks/`** — `useAuth`, `useAccessControl`, `useMutationWithToast`.

---

## 2. Features (Detailed)

### 2.1 Leave & Comp-Off

**Leave types** (from `LeaveTypeEnum`): **Casual**, **Sick**, **Earned**, **WFH**, **Comp-Off**, **Maternity**, **Sabbatical**.

- **Maternity**: Fixed 180-day period; start date selection auto-fills end date.
- **Sabbatical**: Can be open-ended (no end date).
- **Casual**: Consumes casual balance first, then earned balance (earned used first).
- **Deductible days**: Computed excluding weekends and holidays (configurable holiday list).

**Leave statuses**: `PENDING`, `APPROVED`, `REJECTED`, `CANCELLED`, `CANCELLATION_REQUESTED`.

**Flow**:
- Employee applies → manager approves/rejects. On **approval**, balance is deducted; on **cancellation** (by employee or manager), balance is refunded.
- **Comp-off claims**: Separate flow; on approval, one day is added to the user’s comp-off balance.
- All balance changes (deduction, refund, accrual, yearly reset, manual adjustment, initial setup) are recorded in **`user_balance_history`** with change type, previous/new balance, reason, and actor.

**Balance history change types**: `DEDUCTION`, `REFUND`, `ACCRUAL`, `YEARLY_RESET`, `MANUAL_ADJUSTMENT`, `INITIAL`.

### 2.2 Policies & Documents

- Admins upload **policy documents** (e.g. PDFs) **per year**.
- **Quotas** (casual, sick, WFH) are **editable per year**; policies can be soft-deleted (document history preserved).
- Employees **acknowledge each document** individually.
- Admins see **compliance**: Pending / Partial / Complete per user.
- **GET `/policies/documents-by-year`** drives the frontend “Policy Documents” view and acknowledge/report UI.

### 2.3 User Management & Roles

**Roles** (from `UserRole`): **Employee**, **Manager**, **HR**, **Admin**, **Founder**, **Co-founder**, **Intern**, **Contract**.

**Scopes** (from `backend/utils/scopes.py`): Fine-grained permissions, e.g. `read:leaves`, `write:leaves`, `approve:leaves`, `cancel:leaves`, `read:users`, `write:users`, `admin:users`, `read/write:holidays`, `read/write:policies`, `acknowledge:policies`, `admin:system`, `trigger:jobs`, `export:data`. Each role is mapped to a default set of scopes (e.g. Manager gets approve, HR/Admin/Founder/Co-founder get broader access).

- **User management**: Create/update users, assign **manager**, set **leave balances**, **roles**, and **staff roles** (e.g. HR). **Bootstrap** (`POST /admin/bootstrap`) creates the database (if needed), all tables via `init_db()`, seeds roles and a default admin — no Alembic run required for first-time deploy. Bootstrap can be allowed once without auth via `ALLOW_BOOTSTRAP_NO_AUTH=true`.
- **Admin bootstrap credentials** come from `.env`: `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `ADMIN_EMPLOYEE_ID`, `ADMIN_FULL_NAME`.

### 2.4 Team View

- **Team page** is available to **all authenticated users** (sidebar: “Team”).
- **Manager / HR / Admin / Founder / Co-founder**: See **Pending Requests** (leave/comp-off to approve), **My Team** roster (direct reports or all active users via `GET /manager/team`), and **Team presence** for a chosen date (`GET /manager/team/presence`).
- **Employee / Intern / Contract**: See **My Teammates** — colleagues who report to the **same manager** (`GET /manager/team/peers`). If the user has no manager or is the only report, the list is empty.

### 2.5 Holidays & Scheduler

- **Holidays**: Add manually or **bulk-import via CSV**. Used when computing working days for leave. **Holiday Planner** (admin/hr/founder/co_founder): list, add, delete, import; **Refresh** re-fetches the list from the API.
- **Scheduler** (in `backend/services/scheduler.py`):  
  - **Monthly accrual**: Runs on the 1st of each month; adds 1/12 of casual quota to all active users. Idempotent: logs to **job_logs** as `monthly_accrual_YYYY_MM` and skips if already run that month.  
  - **Yearly reset**: Runs Jan 1; CL = 0, SL/WFH = quota, EL = 50% carry-forward; then triggers monthly accrual. Logs to **job_logs** as `yearly_reset_YYYY` so manual trigger is locked out for that year.  
  Balance history records accruals and resets.
- **Manual triggers** (Holiday Planner UI, admin/hr/founder/co_founder only):  
  - **Run Monthly Accrual** — calls `POST /admin/trigger-accrual`. **Technical lockout**: disabled when accrual already ran this month (via **GET /admin/job-status**); backend returns 409 if called again.  
  - **Reset Manually (Yearly)** — calls `POST /admin/yearly-reset`. **Technical lockout**: disabled when yearly reset already ran this year (scheduler or manual); backend returns 409 if called again.  
  **GET /admin/job-status** returns `monthly_accrual_run_this_month` and `yearly_reset_run_this_year` so the frontend can disable the buttons.

### 2.6 Profile & Security

- **User profile**: Personal/family/emergency details, date of birth, profile picture (and related fields in `UserProfile`).
- **Auth**: JWT with role-based scopes; **password reset** (forgot-password flow); optional **“reset required”** on first login (force-reset flow).

### 2.7 Email

- Leave approval/rejection (and related) emails can be sent via **SMTP** (`EMAIL_METHOD=smtp`) or **Microsoft Graph** (`EMAIL_METHOD=graph`). With Graph, emails can be sent “from” the manager’s address when configured.

---

## 3. How It Fits Together

### 3.1 First-Time Deploy

1. Configure **`.env`** (DB, JWT, admin bootstrap vars, optional email).
2. Call **`POST /admin/bootstrap`** (with `ALLOW_BOOTSTRAP_NO_AUTH=true` if no admin exists). This:
   - Ensures the database exists,
   - Runs `init_db()` (creates all tables from SQLAlchemy models),
   - Seeds roles and role–scope mappings,
   - Creates the default admin user from `.env`.
3. No Alembic run is required for the first run. For **schema changes** later, use Alembic migrations in `alembic/versions/`.

### 3.2 Data Model (Main Entities)

| Area | Tables / Concepts |
|------|-------------------|
| **Users** | `users`, `user_profiles`, `user_roles`, `staff_roles`, `user_leave_balances`, `user_balance_history` |
| **Leave** | `leave_requests`, comp-off claims (e.g. in same or related table), leave types and statuses |
| **Policies** | `policies` (with soft-delete), policy documents per year, acknowledgments |
| **Org** | `holidays`, `roles`, `role_scopes` |
| **Jobs** | `job_logs` (monthly accrual, yearly reset, manual runs for lockout) |
| **Audit** | `audit_logs` |

Balance history stores: previous balance, new balance, change type, reason, related leave id (if any), and who performed the change.

### 3.3 API Structure

- **Auth**: login, refresh, forgot-password, reset-password, me.
- **Users**: CRUD, me, bootstrap, balance updates, etc.
- **Manager**: **GET /manager/team** — team roster (manager+ only); **GET /manager/team/peers** — teammates under same manager (any user); **GET /manager/team/presence** — present/on leave by date (manager+). Leave approvals via leaves routes.
- **Leaves**: apply, list (mine/team), approve/reject/cancel, comp-off claim.
- **Holidays**: CRUD, bulk import, calendar endpoint; **POST /admin/yearly-reset** (locked out if yearly reset already ran this year).
- **Jobs**: **GET /admin/job-status** — returns whether monthly accrual and yearly reset have run for the current period (for UI lockout). **POST /admin/trigger-accrual** — manual monthly accrual (locked out if already run this month).
- **Policies**: CRUD, documents-by-year, acknowledge, compliance/reports.

Routers are mounted in `backend/main.py`; no global API prefix in the overview (check `main.py` for exact paths). Static files served from `/static`.

### 3.4 Role → Access (Short)

- **Employee / Intern / Contract**: Own leave, policies, holidays; **Team page** shows “My Teammates” (peers under same manager via `GET /manager/team/peers`); no user admin.
- **Manager**: Plus approve/cancel team leaves, **My Team** roster (direct reports), **Team presence** by date.
- **HR**: Plus user management, export, policy/holiday write, **trigger jobs** (Run Monthly Accrual on Holiday Planner); same team/presence view as manager.
- **Admin / Founder / Co-founder**: Full access including system admin and trigger jobs; team view shows all active users. Holiday Planner: Run Monthly Accrual and Reset Manually (Yearly), both with technical lockout when the scheduled job already ran.

---

## 4. Repo & Run

### 4.1 Repository Structure (High Level)

```
lms/
├── backend/          # FastAPI app
│   ├── main.py       # App entry, lifespan, routers
│   ├── db.py         # DB engine, session, init_db
│   ├── models/       # SQLAlchemy + enums
│   ├── routes/       # auth, users, manager, leaves, holidays, policies
│   ├── services/     # seed, email, scheduler, balance_history, audit
│   └── utils/        # scopes, security, leave_utils, etc.
├── frontend/         # Next.js app (App Router)
│   └── src/
│       ├── app/      # Routes and pages
│       ├── components/
│       ├── hooks/, lib/, types/
├── alembic/          # Migrations (for schema changes after bootstrap)
├── .env              # Backend config (do not commit secrets)
├── requirements.txt  # Python deps
└── PROJECT_OVERVIEW.md, README.md, DEPLOYMENT.md
```

### 4.2 Configuration (.env)

- **Security**: `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`
- **Database**: `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`
- **Admin bootstrap**: `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `ADMIN_EMPLOYEE_ID`, `ADMIN_FULL_NAME`
- **Bootstrap gate**: `ALLOW_BOOTSTRAP_NO_AUTH` (set `false` after first admin exists)
- **Email**: `EMAIL_METHOD` (smtp | graph), `MAIL_*` for SMTP; optional Graph vars
- **Frontend**: `FRONTEND_URL` (e.g. for links in emails)
- **Logging**: `LOG_LEVEL` (optional)

### 4.3 Run Commands

**Backend** (from repo root, e.g. `lms/`):

```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Runs by default at `http://localhost:8000`. Config from `.env`.

**Frontend**:

```bash
cd frontend
npm install
npm run dev
```

Uses React Query and axios to talk to the backend; auth via JWT in headers (e.g. Bearer).

**Database**: MySQL must be running; create the DB manually or let bootstrap create it (if your setup allows). For schema evolution after first deploy, use Alembic: `alembic upgrade head`, etc.

---

## 5. Where to Look Next

- **Setup and day-to-day run**: `README.md`
- **Deploy and production checklist**: `DEPLOYMENT.md`
- **API contracts and table definitions**: OpenAPI (FastAPI’s `/docs`) and the codebase (`backend/routes/`, `backend/models/`).
