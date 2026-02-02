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
            console.log('API Request:', config.method?.toUpperCase(), (config.baseURL ?? '') + (config.url ?? ''));
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Safely stringify for logging (handles circular refs and non-JSON values)
function safeStringify(obj: unknown, space?: number): string {
    try {
        const seen = new WeakSet();
        return JSON.stringify(obj, (_, v) => {
            if (typeof v === 'object' && v !== null) {
                if (seen.has(v)) return '[Circular]';
                seen.add(v);
            }
            return v;
        }, space);
    } catch {
        return String(obj);
    }
}

// Response Interceptor
api.interceptors.response.use(
    (response) => response,
    (error) => {
        // Log error details for debugging with better serialization
        if (error.response) {
            const status = error.response.status;
            const statusText = error.response.statusText;
            const data = error.response.data;
            const method = error.config?.method?.toUpperCase();
            const url = error.config?.url;
            const baseURL = error.config?.baseURL;
            const fullURL = baseURL && url ? baseURL + url : url;

            // Single log line: method, URL, status, and body (no duplicate "Full error.response")
            console.error(
                `Axios error: ${method} ${fullURL} → ${status} ${statusText}`,
                typeof data === 'object' && data !== null ? safeStringify(data) : data
            );
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
