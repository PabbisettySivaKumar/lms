import axios from 'axios';

// Create a configured axios instance
export const api = axios.create({
    baseURL: '/api', // Proxied to backend via next.config.ts
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
