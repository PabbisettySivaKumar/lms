'use client';

import { useState, useEffect } from 'react';
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
    const [token, setToken] = useState('');

    useEffect(() => {
        const tokenParam = searchParams.get('token');
        if (tokenParam) {
            setToken(tokenParam);
        }
    }, [searchParams]);

    const {
        register,
        handleSubmit,
        setValue,
        formState: { errors },
    } = useForm<ResetPasswordSchema>({
        resolver: zodResolver(resetPasswordSchema),
        defaultValues: {
            token: token,
        },
    });

    // Update token when it's loaded from URL
    useEffect(() => {
        if (token) {
            setValue('token', token);
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
                        Enter your reset token and new password
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="token">Reset Token</Label>
                            <Input
                                id="token"
                                type="text"
                                placeholder="Enter the token from your email"
                                {...register('token')}
                                defaultValue={token}
                            />
                            {errors.token && (
                                <p className="text-sm text-red-500">{errors.token.message}</p>
                            )}
                            <p className="text-xs text-slate-500">
                                Check your email for the reset token (expires in 15 minutes)
                            </p>
                        </div>
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
