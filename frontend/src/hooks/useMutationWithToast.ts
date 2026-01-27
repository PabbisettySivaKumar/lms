/**
 * Custom hook for mutations with automatic toast notifications
 */
import { useMutation, useQueryClient, UseMutationOptions } from '@tanstack/react-query';
import { toast } from 'sonner';
import api from '@/lib/axios';
import { AxiosError } from 'axios';

interface MutationConfig<TData, TVariables> {
    mutationFn: (variables: TVariables) => Promise<TData>;
    successMessage?: string | ((data: TData, variables: TVariables) => string);
    errorMessage?: string;
    invalidateQueries?: string[];
    onSuccess?: (data: TData, variables: TVariables) => void;
    onError?: (error: AxiosError, variables: TVariables) => void;
}

export function useMutationWithToast<TData = any, TVariables = any>(
    config: MutationConfig<TData, TVariables>
) {
    const queryClient = useQueryClient();
    const {
        mutationFn,
        successMessage = 'Operation completed successfully',
        errorMessage = 'Operation failed',
        invalidateQueries = [],
        onSuccess,
        onError
    } = config;

    return useMutation<TData, AxiosError, TVariables>({
        mutationFn,
        onSuccess: (data, variables) => {
            // Handle successMessage as either string or function
            const message = typeof successMessage === 'function' 
                ? successMessage(data, variables) 
                : successMessage;
            toast.success(message);
            
            // Invalidate queries
            invalidateQueries.forEach(queryKey => {
                queryClient.invalidateQueries({ queryKey: [queryKey] });
            });
            
            onSuccess?.(data, variables);
        },
        onError: (error, variables) => {
            const errorData = error.response?.data as any;
            const errorDetail = (typeof errorData === 'object' && errorData !== null && 'detail' in errorData)
                ? errorData.detail
                : errorMessage;
            toast.error(typeof errorDetail === 'string' ? errorDetail : errorMessage);
            onError?.(error, variables);
        }
    });
}

/**
 * Helper to extract error message from API errors
 */
export function getErrorMessage(error: unknown, fallback: string = 'An error occurred'): string {
    if (error instanceof Error) {
        return error.message;
    }
    if (typeof error === 'object' && error !== null && 'response' in error) {
        const axiosError = error as AxiosError;
        const detail = axiosError.response?.data as any;
        if (typeof detail?.detail === 'string') {
            return detail.detail;
        }
        if (Array.isArray(detail?.detail)) {
            return detail.detail.map((err: any) => err.msg || err.message).join(', ');
        }
    }
    return fallback;
}
