/**
 * Reusable status badge component
 */
import { Badge } from '@/components/ui/badge';
import { LeaveStatus } from '@/types';
import { memo } from 'react';

interface StatusBadgeProps {
    status: string;
    variant?: 'default' | 'secondary' | 'destructive' | 'outline';
}

const statusConfig: Record<string, { variant: StatusBadgeProps['variant']; className: string }> = {
    APPROVED: {
        variant: 'default',
        className: 'bg-green-100 text-green-800 hover:bg-green-100 border-green-200'
    },
    PENDING: {
        variant: 'secondary',
        className: 'bg-yellow-100 text-yellow-800 hover:bg-yellow-100 border-yellow-200'
    },
    REJECTED: {
        variant: 'destructive',
        className: 'bg-red-100 text-red-800 hover:bg-red-100 border-red-200'
    },
    CANCELLED: {
        variant: 'outline',
        className: 'bg-gray-100 text-gray-800 border-gray-200'
    },
    CANCELLATION_REQUESTED: {
        variant: 'secondary',
        className: 'bg-orange-100 text-orange-800 hover:bg-orange-100 border-orange-200'
    }
};

export const StatusBadge = memo(function StatusBadge({ status, variant }: StatusBadgeProps) {
    const config = statusConfig[status] || { variant: 'outline' as const, className: '' };
    const finalVariant = variant || config.variant;

    return (
        <Badge variant={finalVariant} className={config.className}>
            {status.replace('_', ' ')}
        </Badge>
    );
});
