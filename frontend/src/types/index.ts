/**
 * Centralized type definitions for the application
 */

export interface User {
    id: number | string; // Backend returns integer, but we support both for compatibility
    _id?: string; // Backward compatibility - backend may return this as string
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
    dob?: string;
    blood_group?: string;
    address?: string;
    father_name?: string;
    mother_name?: string;
    spouse_name?: string;
    children_names?: string;
    permanent_address?: string;
    emergency_contact_name?: string;
    emergency_contact_phone?: string;
    employee_type?: string;
    employee_id: string;
}

export interface LeaveRequest {
    id: number | string; // Backend returns integer
    _id?: string; // Backward compatibility
    applicant_id?: number | string;
    applicant_name?: string;
    type: string;
    start_date: string;
    end_date: string | null;
    status: string;
    deductible_days: number;
    reason: string;
}

export interface Holiday {
    id: number | string; // Backend returns integer
    _id?: string; // Backward compatibility
    name: string;
    date: string;
    is_optional: boolean;
    year?: number;
}

export interface ManagerData {
    employee_id: string;
    full_name: string;
    name?: string;
    email: string;
    role?: string;
}

export type UserRole = 'employee' | 'manager' | 'hr' | 'founder' | 'admin' | 'intern' | 'contract';

export type LeaveStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'CANCELLED' | 'CANCELLATION_REQUESTED';

export type LeaveType = 'CASUAL' | 'SICK' | 'COMP_OFF' | 'MATERNITY' | 'SABBATICAL' | 'WFH';
