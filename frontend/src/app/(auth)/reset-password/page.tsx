'use client';

import { useState, useEffect, useMemo } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { toast } from 'sonner';
import { Loader2, ArrowLeft } from 'lucide-react';

import api from '@/lib/axios';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
    Card,
    CardContent,
    CardDescription,
    CardFooter,
    CardHeader,
    CardTitle,
} from '@/components/ui/card';

// Validation Schema
const resetPasswordSchema = z.object({
    token: z.string().min(1, 'Token is required'),
    new_password: z.string().min(6, 'Password must be at least 6 characters'),
    confirm_password: z.string().min(1, 'Please confirm your password'),
}).refine((data) => data.new_password === data.confirm_password, {
    message: "Passwords don't match",
    path: ["confirm_password"],
});

type ResetPasswordSchema = z.infer<typeof resetPasswordSchema>;

export default function ResetPasswordPage() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const [loading, setLoading] = useState(false);
    
    // Extract token from URL - use useMemo to get stable value
    const tokenParam = useMemo(() => searchParams.get('token'), [searchParams]);
    const token = tokenParam || '';

    // Clean URL after extracting token (only once)
    useEffect(() => {
        if (tokenParam) {
            // Remove token from URL for security (replace with clean URL)
            const newUrl = window.location.pathname;
            window.history.replaceState({}, '', newUrl);
        } else {
            // If no token in URL, show error
            toast.error('Invalid or missing reset token. Please use the link from your email.');
        }
    }, [tokenParam]);

    const {
        register,
        handleSubmit,
        setValue,
        formState: { errors },
    } = useForm<ResetPasswordSchema>({
        resolver: zodResolver(resetPasswordSchema),
        defaultValues: {
            token: '',
        },
    });

    // Update token in form when it's loaded from URL
    useEffect(() => {
        if (token) {
            setValue('token', token, { shouldValidate: false });
        }
    }, [token, setValue]);

    const onSubmit = async (data: ResetPasswordSchema) => {
        setLoading(true);
        try {
            await api.post('/auth/reset-password', {
                token: data.token,
                new_password: data.new_password,
            });
            toast.success('Password reset successfully! You can now login.');
            router.push('/login');
        } catch (error: any) {
            const errorMessage = error.response?.data?.detail || 'Failed to reset password. Token may be invalid or expired.';
            toast.error(errorMessage);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex items-center justify-center min-h-screen bg-slate-50 dark:bg-slate-900">
            <Card className="w-full max-w-md shadow-lg">
                <CardHeader className="space-y-1">
                    <CardTitle className="text-2xl font-bold text-center">Reset Password</CardTitle>
                    <CardDescription className="text-center">
                        Enter your new password
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                        {/* Hidden token field - token is extracted from URL and stored securely */}
                        <input
                            type="hidden"
                            {...register('token')}
                            value={token}
                        />
                        {!token && (
                            <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-md">
                                <p className="text-sm text-yellow-800 dark:text-yellow-200">
                                    No reset token found. Please use the link from your email.
                                </p>
                            </div>
                        )}
                        <div className="space-y-2">
                            <Label htmlFor="new_password">New Password</Label>
                            <Input
                                id="new_password"
                                type="password"
                                {...register('new_password')}
                            />
                            {errors.new_password && (
                                <p className="text-sm text-red-500">{errors.new_password.message}</p>
                            )}
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="confirm_password">Confirm Password</Label>
                            <Input
                                id="confirm_password"
                                type="password"
                                {...register('confirm_password')}
                            />
                            {errors.confirm_password && (
                                <p className="text-sm text-red-500">{errors.confirm_password.message}</p>
                            )}
                        </div>
                        <Button type="submit" className="w-full" disabled={loading}>
                            {loading ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    Resetting...
                                </>
                            ) : (
                                'Reset Password'
                            )}
                        </Button>
                    </form>
                </CardContent>
                <CardFooter className="justify-center">
                    <Link
                        href="/login"
                        className="text-sm text-blue-600 hover:underline flex items-center"
                    >
                        <ArrowLeft className="mr-1 h-3 w-3" />
                        Back to Login
                    </Link>
                </CardFooter>
            </Card>
        </div>
    );
}
