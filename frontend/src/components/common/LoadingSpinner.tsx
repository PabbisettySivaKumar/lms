/**
 * Reusable loading spinner component
 */
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface LoadingSpinnerProps {
    size?: 'sm' | 'md' | 'lg';
    className?: string;
    text?: string;
}

export function LoadingSpinner({ size = 'md', className, text }: LoadingSpinnerProps) {
    const sizeClasses = {
        sm: 'h-4 w-4',
        md: 'h-8 w-8',
        lg: 'h-12 w-12'
    };

    return (
        <div className={cn('flex items-center justify-center gap-2', className)}>
            <Loader2 className={cn('animate-spin text-primary', sizeClasses[size])} />
            {text && <span className="text-sm text-slate-600">{text}</span>}
        </div>
    );
}

/**
 * Full page loading component
 */
export function PageLoading({ text = 'Loading...' }: { text?: string }) {
    return (
        <div className="flex h-[50vh] items-center justify-center">
            <LoadingSpinner size="lg" text={text} />
        </div>
    );
}

/**
 * Inline loading component
 */
export function InlineLoading({ className }: { className?: string }) {
    return <LoadingSpinner size="sm" className={className} />;
}
