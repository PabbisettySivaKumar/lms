import axios from 'axios';

const api = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL || '/api', // Use Next.js proxy
});

// Request Interceptor
api.interceptors.request.use(
    (config) => {
        if (typeof window !== 'undefined') {
            const token = localStorage.getItem('access_token');
            if (token) {
                config.headers.Authorization = `Bearer ${token}`;
            }
        }
        // Debug: Log the full URL being requested
        if (process.env.NODE_ENV === 'development') {
            console.log('API Request:', config.method?.toUpperCase(), config.baseURL + config.url);
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Response Interceptor
api.interceptors.response.use(
    (response) => response,
    (error) => {
        // Log error details for debugging
        if (error.response) {
            console.error('Axios error response:', {
                status: error.response.status,
                statusText: error.response.statusText,
                data: error.response.data,
                headers: error.response.headers,
                config: {
                    method: error.config?.method,
                    url: error.config?.url,
                    baseURL: error.config?.baseURL,
                }
            });
        } else if (error.request) {
            // Request was made but no response received
            console.error('Axios error - no response:', {
                request: error.request,
                message: error.message,
                config: {
                    method: error.config?.method,
                    url: error.config?.url,
                    baseURL: error.config?.baseURL,
                }
            });
        } else {
            // Error setting up the request
            console.error('Axios error - request setup failed:', error.message);
        }
        
        if (error.response?.status === 401) {
            if (typeof window !== 'undefined') {
                localStorage.removeItem('access_token');
                window.location.href = '/login';
            }
        }
        return Promise.reject(error);
    }
);

export default api;
