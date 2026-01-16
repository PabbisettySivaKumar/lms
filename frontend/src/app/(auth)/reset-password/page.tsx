'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { toast } from 'sonner';
import { Loader2, ArrowLeft } from 'lucide-react';

import { useAuth } from '@/hooks/useAuth';
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
const resetPasswordSchema = z
    .object({
        token: z.string().min(1, { message: 'Token is required' }),
        newPassword: z.string().min(6, { message: 'Password must be at least 6 characters' }),
        confirmPassword: z.string().min(1, { message: 'Confirm Password is required' }),
    })
    .refine((data) => data.newPassword === data.confirmPassword, {
        path: ['confirmPassword'],
        message: "Passwords don't match",
    });

type ResetPasswordSchema = z.infer<typeof resetPasswordSchema>;

import { useSearchParams } from 'next/navigation';

// ... (existing imports)

export default function ResetPasswordPage() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const tokenFromUrl = searchParams.get('token') || '';

    const { resetPassword } = useAuth();
    const [loading, setLoading] = useState(false);

    const {
        register,
        handleSubmit,
        formState: { errors },
    } = useForm<ResetPasswordSchema>({
        resolver: zodResolver(resetPasswordSchema),
        defaultValues: {
            token: tokenFromUrl
        }
    });

    const onSubmit = async (data: ResetPasswordSchema) => {
        setLoading(true);
        try {
            await resetPassword(data.token, data.newPassword);
            toast.success('Password reset successfully. Please login.');
            router.push('/login');
        } catch (error: any) {
            console.error(error);
            const msg = error.response?.data?.detail || 'Failed to reset password';
            toast.error(msg);
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
                        Enter your token and new password
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                        {!tokenFromUrl ? (
                            <div className="space-y-2">
                                <Label htmlFor="token">Reset Token</Label>
                                <div className="text-xs text-slate-500 mb-1">
                                    Paste the token received in your email
                                </div>
                                <Input
                                    id="token"
                                    placeholder="Paste token here"
                                    {...register('token')}
                                />
                                {errors.token && (
                                    <p className="text-sm text-red-500">{errors.token.message}</p>
                                )}
                            </div>
                        ) : (
                            <input type="hidden" {...register('token')} />
                        )}
                        <div className="space-y-2">
                            <Label htmlFor="newPassword">New Password</Label>
                            <Input
                                id="newPassword"
                                type="password"
                                {...register('newPassword')}
                            />
                            {errors.newPassword && (
                                <p className="text-sm text-red-500">{errors.newPassword.message}</p>
                            )}
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="confirmPassword">Confirm Password</Label>
                            <Input
                                id="confirmPassword"
                                type="password"
                                {...register('confirmPassword')}
                            />
                            {errors.confirmPassword && (
                                <p className="text-sm text-red-500">{errors.confirmPassword.message}</p>
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
                <CardFooter className="justify-center border-t p-4">
                    <Link
                        href="/login"
                        className="text-sm font-medium text-blue-600 hover:underline flex items-center"
                    >
                        <ArrowLeft className="mr-2 h-4 w-4" />
                        Back to login
                    </Link>
                </CardFooter>
            </Card>
        </div>
    );
}
