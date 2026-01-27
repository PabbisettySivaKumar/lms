import { create } from 'zustand';
import api from '@/lib/axios';

interface User {
    id: number | string; // Backend returns integer, support both for compatibility
    _id?: string; // Backward compatibility
    email: string;
    full_name: string;
    role: string;
    is_active: boolean;
    joining_date?: string;
    manager_id?: number | string; // Can be integer or string
    manager_name?: string;
    casual_balance: number;
    sick_balance: number;
    earned_balance: number;
    comp_off_balance: number;
    wfh_balance: number;

    // Personal for Profile
    dob?: string;
    blood_group?: string;
    address?: string;
    father_name?: string;
    father_dob?: string;
    mother_name?: string;
    mother_dob?: string;
    spouse_name?: string;
    spouse_dob?: string;
    children_names?: string;
    permanent_address?: string;
    emergency_contact_name?: string;
    emergency_contact_phone?: string;
    employee_type?: string;
    employee_id: string; // Ensure this is here
    profile_picture_url?: string;
    documents?: {
        name: string;
        url: string;
        saved_filename: string;
        uploaded_at: string;
    }[];
}

interface AuthState {
    user: User | null;
    isLoading: boolean;
    login: (data: { email: string; password: string }) => Promise<boolean>;
    logout: () => void;
    fetchUser: () => Promise<void>;
    refreshUser: () => Promise<void>;
    forgotPassword: (email: string) => Promise<void>;
    resetPassword: (token: string, newPassword: string) => Promise<void>;
    firstLoginReset: (newPassword: string) => Promise<void>;
}

interface LoginResponse {
    access_token: string;
    token_type: string;
    reset_required: boolean;
}

export const useAuth = create<AuthState>((set, get) => ({
    user: null,
    isLoading: false,

    login: async ({ email, password }) => {
        set({ isLoading: true });
        try {
            // Create form data for OAuth2PasswordRequestForm
            const formData = new URLSearchParams();
            formData.append('username', email);
            formData.append('password', password);

            // Send as form-encoded data
            const response = await api.post<LoginResponse>(
                '/auth/login',
                formData.toString(),
                {
                    headers: { 
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                }
            );

            const { access_token, reset_required } = response.data;
            localStorage.setItem('access_token', access_token);
            await get().fetchUser();
            return reset_required;
        } catch (error: any) {
            set({ isLoading: false });
            // Log detailed error for debugging
            if (error.response) {
                // Log the raw error response for debugging
                console.error('Raw error response:', error.response);
                console.error('Error response data:', error.response.data);
                console.error('Error response data type:', typeof error.response.data);
                console.error('Error response data keys:', error.response.data ? Object.keys(error.response.data) : 'no keys');
                
                const errorData = error.response.data;
                // Handle both object and string responses
                let errorMessage = 'Login failed. Please check your credentials.';
                
                if (typeof errorData === 'string') {
                    errorMessage = errorData;
                } else if (errorData && typeof errorData === 'object') {
                    errorMessage = errorData.detail || errorData.message || errorData.error || errorMessage;
                }
                
                console.error('Login error response:', {
                    status: error.response.status,
                    statusText: error.response.statusText,
                    data: errorData,
                    message: errorMessage,
                });
                throw new Error(errorMessage);
            } else if (error.request) {
                console.error('Login error - no response:', error.request);
                throw new Error('Network error. Please check your connection.');
            } else {
                console.error('Login error:', error.message);
                throw new Error(error.message || 'Login failed. Please try again.');
            }
        }
    },

    logout: () => {
        localStorage.removeItem('access_token');
        set({ user: null });
        window.location.href = '/login';
    },

    fetchUser: async () => {
        set({ isLoading: true });
        try {
            const response = await api.get('/users/me');
            set({ user: response.data, isLoading: false });
        } catch (error) {
            set({ user: null, isLoading: false });
            // Optional: logout if fetch fails (401 handled by axios)
        }
    },

    refreshUser: async () => {
        await get().fetchUser();
    },

    forgotPassword: async (email: string) => {
        set({ isLoading: true });
        try {
            await api.post('/auth/forgot-password', { email });
        } finally {
            set({ isLoading: false });
        }
    },

    resetPassword: async (token: string, newPassword: string) => {
        set({ isLoading: true });
        try {
            await api.post('/auth/reset-password', {
                token,
                new_password: newPassword
            });
        } finally {
            set({ isLoading: false });
        }
    },

    firstLoginReset: async (newPassword: string) => {
        set({ isLoading: true });
        try {
            await api.patch('/auth/first-login-reset', {
                new_password: newPassword
            });
            // Update user state locally to reflect reset is done?
            // Usually we just proceed.
        } finally {
            set({ isLoading: false });
        }
    },
}));
