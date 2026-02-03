# Deployment Steps — Leave Management System

Follow these steps when deploying the LMS to a server (first time or update).

---

## Prerequisites

- **Server:** Linux (e.g. Ubuntu) with Python 3.10+, Node.js 18+, and MySQL 8+ (or access to a MySQL instance).
- **Network:** Backend and frontend must be reachable (same host or behind a reverse proxy).

---

## Step 1 — Prepare the server and MySQL

1. Install Python 3.10+, Node.js 18+, and MySQL client if needed.
2. Create a MySQL database (or note host, port, user, password). The app can create the DB on first bootstrap if the user has `CREATE DATABASE` rights.
3. (Optional) Create a dedicated MySQL user for the app with access to that database.

---

## Step 2 — Deploy the code

1. Clone or copy the project to the server (e.g. `/var/www/lms` or your app directory).
2. Ensure `.env` is **not** in git; create it on the server (see Step 3).

---

## Step 3 — Configure environment

**Backend (project root or where you run uvicorn):** Create/edit `.env` with:

```env
# Database (required)
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=your_db_user
MYSQL_PASSWORD=your_db_password
MYSQL_DATABASE=leave_management_db

# Auth (required – use a long random secret in production)
SECRET_KEY=your_long_random_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# First-time only: allow bootstrap without login (set to false after first admin exists)
ALLOW_BOOTSTRAP_NO_AUTH=true

# Frontend URL (for email links, CORS)
FRONTEND_URL=https://your-domain.com

# Email (optional – for notifications)
MAIL_SERVER=smtp.office365.com
MAIL_PORT=587
MAIL_USERNAME=your_email
MAIL_PASSWORD=your_password
MAIL_FROM=noreply@your-domain.com
EMAIL_METHOD=smtp

# Optional
LOG_LEVEL=INFO
```

**Whose email for MAIL_USERNAME / MAIL_PASSWORD?**  
Use a **dedicated sender account** that the app will use to send all system emails (leave approval/rejection, password reset, etc.). **Do not use a personal or end-user email.**

- **Recommended:** A shared or service mailbox, e.g. `noreply@yourcompany.com` or `lms-notifications@yourcompany.com`.
- **Office 365 / Microsoft 365:** Use that mailbox’s login; if MFA is on, create an **App password** in the Microsoft account and put that in `MAIL_PASSWORD`.
- **Same address:** Set `MAIL_FROM` to the same address as `MAIL_USERNAME` (or your chosen “From” display address). Recipients will see this as the sender.
- If you don’t set these, the app still runs; only email notifications (e.g. leave status emails) will not be sent.

**Frontend:** In `frontend/`, create `.env.local` (or set env in your host):

```env
NEXT_PUBLIC_API_URL=https://your-domain.com/api
```

If the frontend is served by the same host and you proxy `/api` to the backend, you can use `NEXT_PUBLIC_API_URL=/api`.

---

## Step 4 — First-time database setup (no Alembic)

1. Set `ALLOW_BOOTSTRAP_NO_AUTH=true` in backend `.env` (only for first deploy when no admin exists).
2. Start the backend once (Step 5). If the DB does not exist, the app will log a warning; that’s expected.
3. Call the bootstrap endpoint once:

   ```bash
   curl -X POST https://your-backend-url/admin/bootstrap
   ```

   Or use the same URL in a browser/Postman. This will:
   - Create the database if it does not exist
   - Create all tables from the current models
   - Seed roles and the default admin user (see `backend/services/seed.py` for default email/password).

4. Set `ALLOW_BOOTSTRAP_NO_AUTH=false` (or remove it) in `.env` and restart the backend.
5. Log in as the seeded admin and change the default password if needed.

**Later deploys:** You do **not** run bootstrap again for the same DB. For schema changes, use Alembic: `alembic upgrade head` (see README or project docs).

---

## Step 5 — Run the backend

From the **project root** (where `backend/` and `requirements.txt` are):

```bash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

- **Production:** Use a process manager (systemd, supervisor) or Gunicorn with Uvicorn workers, e.g.  
  `gunicorn backend.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000`  
  (install gunicorn if you use this.)
- Ensure the app can reach MySQL and that `FRONTEND_URL` and CORS (in `backend/main.py`) match your frontend URL.

---

## Step 6 — Build and run the frontend

From the **frontend** directory:

```bash
npm ci
npm run build
npm start
```

- **Production:** Run `npm start` via a process manager, or serve the output of `npm run build` with a static server if you use static export. Ensure `NEXT_PUBLIC_API_URL` points to your backend (or `/api` if proxied).

---

## Step 7 — Reverse proxy and SSL (recommended)

1. Put Nginx (or Apache/Caddy) in front of the app.
2. Proxy `/api` (and any other backend paths) to `http://127.0.0.1:8000` (or where Uvicorn runs).
3. Serve the Next.js app (or its build) on the same host or subdomain.
4. Enable HTTPS (e.g. Let’s Encrypt) and redirect HTTP to HTTPS.
5. In backend `.env`, set `FRONTEND_URL` to your public frontend URL (e.g. `https://your-domain.com`).

---

## Checklist

- [ ] MySQL is running and reachable; DB user has correct permissions.
- [ ] Backend `.env` has `MYSQL_*`, `SECRET_KEY`, and `FRONTEND_URL`; after first bootstrap, `ALLOW_BOOTSTRAP_NO_AUTH` is false.
- [ ] Frontend `.env.local` has `NEXT_PUBLIC_API_URL` pointing to the backend (or `/api`).
- [ ] Bootstrap was called once for first-time deploy; admin account exists and default password is changed.
- [ ] Backend and frontend are started (or managed by systemd/supervisor).
- [ ] CORS and `FRONTEND_URL` match your frontend domain; HTTPS and reverse proxy are in place for production.

For local/dev setup, see **README.md**.
