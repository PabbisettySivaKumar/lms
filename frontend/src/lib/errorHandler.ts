/**
 * Centralized error handling utilities
 */
import { AxiosError } from 'axios';
import { toast } from 'sonner';

export interface ApiError {
    detail?: string | string[] | { [key: string]: any };
    message?: string;
}

/**
 * Extract error message from API error response
 */
export function extractErrorMessage(error: unknown, fallback: string = 'An error occurred'): string {
    if (error instanceof Error && !(error as AxiosError).response) {
        return error.message;
    }

    const axiosError = error as AxiosError<ApiError>;
    const detail = axiosError.response?.data?.detail;

    if (!detail) {
        return fallback;
    }

    // String error
    if (typeof detail === 'string') {
        return detail;
    }

    // Array of errors (Pydantic validation)
    if (Array.isArray(detail)) {
        return detail.map((err: any) => err.msg || err.message || JSON.stringify(err)).join(', ');
    }

    // Object error
    if (typeof detail === 'object') {
        const messages = Object.entries(detail)
            .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(', ') : value}`)
            .join(', ');
        return messages || fallback;
    }

    return fallback;
}

/**
 * Show error toast with extracted message
 */
export function showErrorToast(error: unknown, fallback: string = 'Operation failed') {
    const message = extractErrorMessage(error, fallback);
    toast.error(message);
}

/**
 * Show success toast
 */
export function showSuccessToast(message: string = 'Operation completed successfully') {
    toast.success(message);
}
