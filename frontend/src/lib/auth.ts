import { api } from './api';

export interface LoginResponse {
    access_token: string;
    token_type: string;
    reset_required: boolean;
}

export interface User {
    id: number | string; // Backend returns integer, support both for compatibility
    _id?: string; // Backward compatibility
    email: string;
    full_name: string;
    role: string;
    is_active: boolean;
    joining_date?: string;
    manager_id?: number | string; // Can be integer or string
    // Balances
    casual_balance: number;
    sick_balance: number;
    earned_balance: number;
    comp_off_balance: number;
    wfh_balance: number;
}

export const auth = {
    login: async (formData: FormData): Promise<LoginResponse> => {
        // OAuth2PasswordRequestForm expects form data, not JSON
        // But axios handles FormData correctly if passed directly
        const response = await api.post<LoginResponse>('/auth/login', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });
        return response.data;
    },

    getMe: async (): Promise<User> => {
        const response = await api.get<User>('/users/me');
        return response.data;
    },

    logout: () => {
        if (typeof window !== 'undefined') {
            localStorage.removeItem('access_token');
        }
    },

    getToken: () => {
        if (typeof window !== 'undefined') {
            return localStorage.getItem('access_token');
        }
        return null;
    },

    setToken: (token: string) => {
        if (typeof window !== 'undefined') {
            localStorage.setItem('access_token', token);
        }
    }
};
