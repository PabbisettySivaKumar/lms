# Leave Management System

A comprehensive web-based application for managing employee leaves, holidays, and company policies. Built with **FastAPI** (Backend), **Next.js** (Frontend), and **MySQL**.

## Features

### 📅 Leave Management
*   **Apply for Leaves**: Support for Casual, Sick, Earned, Comp-Off, Maternity, and Sabbatical leaves.
*   **Maternity Leave**: Start date selection auto-calculates a 180-day leave period.
*   **Sabbatical Leave**: Support for indefinite/open-ended leaves.
*   **Immediate Cancellation**: Employees can cancel approved leaves and receive an immediate balance refund without manager approval.
*   **Calendar View**: Visual calendar showing holidays, weekends, and leave status. Custom weekend logic for long-term leaves (Maternity/Sabbatical).
*   **Interactive Date Picker**: Easy-to-use dialog for selecting single dates or ranges.

### 🏢 Company Policies
*   **Policy Management**: Admins can upload policy documents (PDFs).
*   **Granular Acknowledgment**: Employees must acknowledge each document individually.
*   **Compliance Reports**: Admins can view detailed reports on who has acknowledged which documents, with "Partial", "Pending", or "Complete" statuses.

### 👤 User Profile
*   **Comprehensive Details**: Manage personal info, permanent address, and family details (Spouse, Children).
*   **Balance Tracking**: Real-time view of remaining leave balances.

### 🛠 Admin Features
*   **Leave Reports**: Export approved leave data to CSV for payroll processing and compliance. Includes date range filtering.
*   **Holiday Import**: Bulk import holidays via CSV (supports various formats).
*   **User Management**: create and manage employee accounts.
*   **Yearly Leave Reset**: Automated job to reset casual/sick leaves and earned leaves to 0 (no carry-over).
    *   **Endpoint**: `POST /admin/yearly-reset`
    *   **Logic**: CL=0, SL=policy quota, WFH=quota, EL=0. Idempotent design.

### 💻 UI/UX
*   **Collapsible Sidebar**: Space-saving navigation with expand/collapse toggle.
*   **Dark Mode**: Fully supported dark/light theme switching.

## Tech Stack

*   **Backend**: Python, FastAPI, SQLAlchemy, Pydantic.
*   **Frontend**: TypeScript, Next.js, Tailwind CSS, Shadcn UI, React Query.
*   **Database**: MySQL.
*   **Email**: Office 365 SMTP Integration.

## Setup Instructions

### Prerequisites
*   Python 3.10+
*   Node.js 18+
*   MySQL Instance

### 1. Backend Setup

```bash
# Navigate to root
cd leave_management

# Create Virtual Environment
python3 -m venv venv
source venv/bin/activate

# Install Dependencies
pip install -r requirements.txt

# Run Server
uvicorn backend.main:app --reload
```

Backend will start at `http://localhost:8000`.

### 2. Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install Dependencies
npm install

# Run Development Server
npm run dev
```

Frontend will start at `http://localhost:3000`.

**Optional – Frontend env:** To override the API URL or proxy target, copy `frontend/.env.example` to `frontend/.env` and set `NEXT_PUBLIC_API_URL` and/or `API_BACKEND_URL` as needed. Defaults work for local development (Next.js proxies `/api` to the backend).

### 3. Environment Variables

Create a `.env` file in the **root** directory (for the backend):

```env
# Database
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=leave_management_db

# Security
SECRET_KEY=your_super_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Email (Office 365)
MAIL_USERNAME=your_email@outlook.com
MAIL_PASSWORD=your_password_or_app_password
MAIL_FROM=your_email@outlook.com
MAIL_SERVER=smtp.office365.com
MAIL_PORT=587
MAIL_FROM=your_email@outlook.com
MAIL_PORT=587
MAIL_SERVER=smtp.office365.com

# Admin
ADMIN_EMAIL=admin@example.com
```

## Git Repository Structure

The project uses a **Monorepo** structure:
*   **`frontend/`**: Next.js Client Application.
*   **`backend/`**: FastAPI Backend Application.
*   **`requirements.txt`**: Python dependencies.