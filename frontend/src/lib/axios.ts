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
        // Log error details for debugging with better serialization
        if (error.response) {
            // Safely extract error details
            const errorDetails: any = {
                status: error.response.status,
                statusText: error.response.statusText,
                data: error.response.data,
            };
            
            // Safely extract headers (may have circular references)
            try {
                errorDetails.headers = error.response.headers ? 
                    Object.fromEntries(
                        Object.entries(error.response.headers).slice(0, 10) // Limit to first 10 headers
                    ) : undefined;
            } catch (e) {
                errorDetails.headers = 'Unable to serialize headers';
            }
            
            // Extract config details
            errorDetails.config = {
                method: error.config?.method?.toUpperCase(),
                url: error.config?.url,
                baseURL: error.config?.baseURL,
                fullURL: error.config?.baseURL + error.config?.url,
            };
            
            // Log the error
            console.error('Axios error response:', errorDetails);
            
            // Also log the raw error for debugging
            if (process.env.NODE_ENV === 'development') {
                console.error('Raw error object:', error);
            }
        } else if (error.request) {
            // Request was made but no response received
            console.error('Axios error - no response received:', {
                message: error.message,
                code: error.code,
                config: {
                    method: error.config?.method?.toUpperCase(),
                    url: error.config?.url,
                    baseURL: error.config?.baseURL,
                    fullURL: error.config?.baseURL + error.config?.url,
                }
            });
        } else {
            // Error setting up the request
            console.error('Axios error - request setup failed:', {
                message: error.message,
                stack: error.stack,
            });
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
