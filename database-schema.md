# Database Schema - Entity Relationship Diagram

**Current application: single tenancy only.** One organization; no tenant_id, no tenants table. This schema is what the app uses today.

Includes **users** (identity + auth + hierarchy + employment), **user_profiles** (profile, address, family, emergency contact), and **staff_roles** (one table for all non-employee roles: founder, co_founder, hr, manager). Optimized: profile split; staff_roles with UQ(user_id, role_type) and indexes; composite indexes on hot paths.

```mermaid
erDiagram
    users ||--o| user_profiles : "has"
    users ||--o{ user_documents : "has"
    users ||--o{ leave_requests : "creates"
    users ||--o{ leave_requests : "approves"
    users ||--o{ comp_off_claims : "claims"
    users ||--o{ comp_off_claims : "approves"
    users ||--o{ policy_acknowledgments : "acknowledges"
    users ||--o| users : "managed_by"
    users ||--o{ user_roles : "has"
    users ||--o{ staff_roles : "has non-employee role"
    users ||--o{ user_leave_balances : "has"
    users ||--o{ user_balance_history : "has"
    users ||--o{ notifications : "receives"
    users ||--o{ leave_comments : "creates"
    users ||--o{ leave_attachments : "uploads"
    users ||--o{ audit_logs : "performs"
    policies ||--o{ policy_documents : "has"
    roles ||--o{ user_roles : "assigned_to"
    roles ||--o{ role_scopes : "has"
    leave_requests ||--o{ notifications : "triggers"
    leave_requests ||--o{ leave_comments : "has"
    leave_requests ||--o{ leave_attachments : "has"
    
    users {
        int id PK
        varchar employee_id UK
        varchar email UK
        varchar full_name
        varchar hashed_password
        boolean reset_required
        varchar password_reset_token
        datetime password_reset_expiry
        int manager_id FK
        date joining_date
        boolean is_active
        varchar employee_type
        timestamp created_at
        timestamp updated_at
    }
    
    user_profiles {
        int id PK
        int user_id FK_UK "1:1 with users"
        varchar profile_picture_url
        date dob
        varchar blood_group
        text address
        text permanent_address
        varchar father_name
        date father_dob
        varchar mother_name
        date mother_dob
        varchar spouse_name
        date spouse_dob
        text children_names
        varchar emergency_contact_name
        varchar emergency_contact_phone
        timestamp created_at
        timestamp updated_at
    }
    
    roles {
        int id PK
        varchar name UK
        varchar display_name
        text description
        boolean is_active
        timestamp created_at
    }
    
    role_scopes {
        int id PK
        int role_id FK
        varchar scope_name
        timestamp created_at
    }
    
    user_roles {
        int id PK
        int user_id FK
        int role_id FK
        int assigned_by FK
        timestamp assigned_at
        boolean is_active
    }
    
    staff_roles {
        int id PK
        int user_id FK
        varchar role_type "founder, co_founder, hr, manager"
        varchar department "optional, e.g. for manager/hr"
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }
    
    user_leave_balances {
        int id PK
        int user_id FK
        enum leave_type
        decimal balance
        timestamp updated_at
    }
    
    user_balance_history {
        int id PK
        int user_id FK
        enum leave_type
        decimal previous_balance
        decimal new_balance
        decimal change_amount
        enum change_type
        text reason
        int related_leave_id FK
        int changed_by FK
        timestamp changed_at
    }
    
    user_documents {
        int id PK
        int user_id FK
        varchar name
        varchar url
        timestamp uploaded_at
    }
    
    leave_requests {
        int id PK
        int applicant_id FK
        int approver_id FK
        enum type
        date start_date
        date end_date
        decimal deductible_days
        enum status
        text reason
        timestamp created_at
        timestamp updated_at
        datetime approved_at
        datetime rejected_at
    }
    
    comp_off_claims {
        int id PK
        int claimant_id FK
        int approver_id FK
        date work_date
        text reason
        enum status
        timestamp created_at
        timestamp updated_at
        datetime approved_at
    }
    
    holidays {
        int id PK
        varchar name
        date date UK
        int year
        boolean is_optional
    }
    
    policies {
        int id PK
        int year UK
        int casual_leave_quota
        int sick_leave_quota
        int wfh_quota
        boolean is_active
        varchar document_url
        varchar document_name
        timestamp created_at
        timestamp updated_at
    }
    
    policy_documents {
        int id PK
        int policy_id FK
        varchar name
        varchar url
        timestamp uploaded_at
    }
    
    policy_acknowledgments {
        int id PK
        int user_id FK
        int year
        varchar document_url
        timestamp acknowledged_at
    }
    
    job_logs {
        int id PK
        varchar job_name UK
        timestamp executed_at
        enum status
        json details
        varchar executed_by
    }
    
    notifications {
        int id PK
        int user_id FK
        enum type
        varchar title
        text message
        int related_leave_id FK
        boolean is_read
        timestamp created_at
    }
    
    leave_comments {
        int id PK
        int leave_id FK
        int user_id FK
        text comment
        boolean is_internal
        timestamp created_at
    }
    
    leave_attachments {
        int id PK
        int leave_id FK
        varchar name
        varchar url
        varchar file_type
        int file_size
        int uploaded_by FK
        timestamp uploaded_at
    }
    
    audit_logs {
        int id PK
        int user_id FK
        varchar action
        varchar resource_type
        int resource_id
        json old_values
        json new_values
        varchar ip_address
        text user_agent
        timestamp created_at
    }
```

---

## Schema optimizations

### 1. Users split: `users` + `user_profiles`

| Table | Purpose | Columns |
|-------|---------|--------|
| **users** | Identity, auth, hierarchy, employment | id, employee_id, email, full_name, hashed_password, reset_required, password_reset_token, password_reset_expiry, manager_id, joining_date, is_active, employee_type, created_at, updated_at |
| **user_profiles** | Profile, address, family, emergency contact (1:1 per user) | id, user_id (FK, unique), profile_picture_url, dob, blood_group, address, permanent_address, father_name, father_dob, mother_name, mother_dob, spouse_name, spouse_dob, children_names, emergency_contact_name, emergency_contact_phone, created_at, updated_at |

**Benefits:** Auth and list users only touch `users`; profile edits touch `user_profiles`. Lazy-load profile when needed.

**Constraint:** `user_profiles.user_id` unique (1:1 with users).

---

### 2. Staff roles: one table for all non-employee roles

| Column | Type | Notes |
|--------|------|--------|
| id | PK | |
| user_id | FK → users.id | |
| role_type | varchar/enum | founder, co_founder, hr, manager |
| department | varchar, nullable | Optional; e.g. for manager/hr |
| is_active | boolean | default true |
| created_at, updated_at | timestamp | |

**Constraints:** UQ(user_id, role_type) — one row per (user, role); same user can be both hr and manager (two rows).  
**Validation:** role_type in (founder, co_founder, hr, manager) — application or CHECK.

**Benefits:** One table, one migration, one code path; easy to add a new role (new value); "list all managers" = WHERE role_type = 'manager' AND is_active.

---

### 3. Indexes (hot paths)

| Table | Index | Use |
|-------|--------|-----|
| **users** | (email), (employee_id), (manager_id), (is_active), (created_at) | Login, list users, team by manager |
| **user_profiles** | (user_id) unique | Join / 1:1 lookup |
| **user_roles** | (user_id), (role_id), UQ(user_id, role_id) | Role check, avoid duplicate assignment |
| **staff_roles** | (user_id), (role_type), (is_active), UQ(user_id, role_type) | "Is manager?", "List managers" |
| **user_leave_balances** | UQ(user_id, leave_type) | Per-user per-type balance |
| **leave_requests** | (applicant_id, status), (approver_id, status), (start_date, end_date), (created_at) | Pending list, presence check, overlap check |
| **comp_off_claims** | (claimant_id, status), (approver_id, status) | Pending list |
| **policy_acknowledgments** | (user_id, year) | One acknowledgment per user per year |
| **holidays** | (date) unique, (year) | By date, by year |
| **policies** | (year) unique, (is_active) | Current policy |
| **notifications** | (user_id, is_read), (user_id, created_at) | Unread list, recent |
| **audit_logs** | (user_id, created_at), (created_at, action) | User activity, recent actions |

---

### 4. Other constraints

- **user_leave_balances:** UQ(user_id, leave_type) — one balance row per user per leave type.
- **policy_acknowledgments:** UQ(user_id, year) — one acknowledgment per user per policy year (if your business rule is per year).
