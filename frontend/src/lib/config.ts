/**
 * Backend URL for API requests. Read from .env (backend_url).
 * Next.js exposes it to the browser via next.config env as NEXT_PUBLIC_BACKEND_URL.
 * - Unset/empty: use Next.js proxy (/api -> backend).
 * - Set in .env as backend_url=http://127.0.0.1:8000: call backend directly.
 */
const raw = (process.env.NEXT_PUBLIC_BACKEND_URL ?? process.env.NEXT_PUBLIC_API_URL ?? '').trim();
export const BACKEND_URL =
    raw !== '' ? raw.replace(/\/$/, '') : '/api';
