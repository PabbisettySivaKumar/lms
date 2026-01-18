'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { toast } from 'sonner';
import { Loader2, ArrowLeft, LogOut } from 'lucide-react';

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
const forceResetSchema = z
    .object({
        newPassword: z.string().min(6, { message: 'Password must be at least 6 characters' }),
        confirmPassword: z.string().min(1, { message: 'Confirm Password is required' }),
    })
    .refine((data) => data.newPassword === data.confirmPassword, {
        path: ['confirmPassword'],
        message: "Passwords don't match",
    });

type ForceResetSchema = z.infer<typeof forceResetSchema>;

export default function ForceResetPage() {
    const router = useRouter();
    const { firstLoginReset, logout } = useAuth();
    const [loading, setLoading] = useState(false);

    const {
        register,
        handleSubmit,
        formState: { errors },
    } = useForm<ForceResetSchema>({
        resolver: zodResolver(forceResetSchema),
    });

    const onSubmit = async (data: ForceResetSchema) => {
        setLoading(true);
        try {
            await firstLoginReset(data.newPassword);
            toast.success('Password updated successfully!');
            router.push('/dashboard');
        } catch (error: any) {
            console.error(error);
            const msg = error.response?.data?.detail || 'Failed to update password';
            toast.error(msg);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex items-center justify-center min-h-screen bg-slate-50 dark:bg-slate-900">
            <Card className="w-full max-w-md shadow-lg">
                <CardHeader className="space-y-1">
                    <CardTitle className="text-2xl font-bold text-center">Set New Password</CardTitle>
                    <CardDescription className="text-center">
                        Secure your account by setting a new password.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
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
                                    Updating...
                                </>
                            ) : (
                                'Set Password & Continue'
                            )}
                        </Button>
                    </form>
                </CardContent>
                <CardFooter className="justify-center border-t p-4">
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={logout}
                        className="text-slate-500 hover:text-red-600"
                    >
                        <LogOut className="mr-2 h-4 w-4" />
                        Log out
                    </Button>
                </CardFooter>
            </Card>
        </div>
    );
}
