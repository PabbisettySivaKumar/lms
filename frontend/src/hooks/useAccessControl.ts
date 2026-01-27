/**
 * Custom hook for role-based access control
 */
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from './useAuth';
import { UserRole } from '@/types';

interface UseAccessControlOptions {
    allowedRoles: UserRole[];
    redirectTo?: string;
}

export function useAccessControl({ allowedRoles, redirectTo = '/dashboard' }: UseAccessControlOptions) {
    const { user, isLoading } = useAuth();
    const router = useRouter();

    useEffect(() => {
        if (!isLoading && user) {
            if (!allowedRoles.includes(user.role as UserRole)) {
                router.push(redirectTo);
            }
        }
    }, [user, isLoading, router, allowedRoles, redirectTo]);

    return {
        hasAccess: user ? allowedRoles.includes(user.role as UserRole) : false,
        isLoading,
        user
    };
}
