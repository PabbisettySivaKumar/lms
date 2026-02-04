import axios from 'axios';
import { BACKEND_URL } from './config';

// Create a configured axios instance (backend URL from .env NEXT_PUBLIC_API_URL)
export const api = axios.create({
    baseURL: BACKEND_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Request Interceptor: Attach Token
api.interceptors.request.use(
    (config) => {
        if (typeof window !== 'undefined') {
            const token = localStorage.getItem('access_token');
            if (token) {
                config.headers.Authorization = `Bearer ${token}`;
            }
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Response Interceptor: Handle 401 (Optional: Redirect to login)
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            // Logic to handle unauthorized access (e.g., clear token, redirect)
            // localStorage.removeItem('access_token');
            // window.location.href = '/login'; 
        }
        return Promise.reject(error);
    }
);
