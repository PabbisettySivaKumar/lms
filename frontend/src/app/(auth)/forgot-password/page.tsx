'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
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
const forgotPasswordSchema = z.object({
    email: z.string().email({ message: 'Invalid email address' }),
});

type ForgotPasswordSchema = z.infer<typeof forgotPasswordSchema>;

export default function ForgotPasswordPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(false);
    const [emailSent, setEmailSent] = useState(false);
    const [resetToken, setResetToken] = useState<string | null>(null);
    const [resetUrl, setResetUrl] = useState<string | null>(null);

    const {
        register,
        handleSubmit,
        formState: { errors },
    } = useForm<ForgotPasswordSchema>({
        resolver: zodResolver(forgotPasswordSchema),
    });

    const onSubmit = async (data: ForgotPasswordSchema) => {
        setLoading(true);
        try {
            const response = await api.post<{ message: string; reset_token?: string; reset_url?: string }>('/auth/forgot-password', { email: data.email });
            
            // Check if token is returned (development mode when email fails)
            if (response.data.reset_token) {
                setResetToken(response.data.reset_token);
                setResetUrl(response.data.reset_url || null);
                toast.info('Email sending failed. Use the token shown below (development mode).');
            } else {
                toast.success('If the email exists, a reset link has been sent.');
            }
            setEmailSent(true);
        } catch (error: any) {
            // Backend returns 200 even if email doesn't exist (security)
            setEmailSent(true);
            toast.success('If the email exists, a reset link has been sent.');
        } finally {
            setLoading(false);
        }
    };

    if (emailSent) {
        return (
            <div className="flex items-center justify-center min-h-screen bg-slate-50 dark:bg-slate-900">
                <Card className="w-full max-w-md shadow-lg">
                    <CardHeader className="space-y-1">
                        <CardTitle className="text-2xl font-bold text-center">Check Your Email</CardTitle>
                        <CardDescription className="text-center">
                            {resetToken 
                                ? "Email sending failed. Use the token below (development mode)."
                                : "If an account with that email exists, we've sent password reset instructions."}
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {resetToken ? (
                            <div className="space-y-3 p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-md">
                                <p className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
                                    Development Mode - Reset Token:
                                </p>
                                <div className="space-y-2">
                                    <div>
                                        <Label className="text-xs text-yellow-700 dark:text-yellow-300">Token:</Label>
                                        <p className="text-sm font-mono bg-white dark:bg-slate-800 p-2 rounded border break-all">
                                            {resetToken}
                                        </p>
                                    </div>
                                    {resetUrl && (
                                        <div>
                                            <Label className="text-xs text-yellow-700 dark:text-yellow-300">Reset URL:</Label>
                                            <a 
                                                href={resetUrl}
                                                className="text-sm text-blue-600 hover:underline break-all block"
                                            >
                                                {resetUrl}
                                            </a>
                                        </div>
                                    )}
                                </div>
                                <p className="text-xs text-yellow-700 dark:text-yellow-300">
                                    ⚠️ This token expires in 15 minutes. Update your email configuration to receive tokens via email.
                                </p>
                            </div>
                        ) : (
                            <p className="text-sm text-slate-600 dark:text-slate-400 text-center">
                                Please check your email inbox and follow the instructions to reset your password.
                                The reset token will expire in 15 minutes.
                            </p>
                        )}
                    </CardContent>
                    <CardFooter className="flex flex-col space-y-2">
                        {resetUrl && (
                            <Button
                                className="w-full"
                                onClick={() => window.location.href = resetUrl}
                            >
                                Go to Reset Password Page
                            </Button>
                        )}
                        <Button
                            variant="outline"
                            className="w-full"
                            onClick={() => {
                                setEmailSent(false);
                                setResetToken(null);
                                setResetUrl(null);
                                router.push('/login');
                            }}
                        >
                            <ArrowLeft className="mr-2 h-4 w-4" />
                            Back to Login
                        </Button>
                    </CardFooter>
                </Card>
            </div>
        );
    }

    return (
        <div className="flex items-center justify-center min-h-screen bg-slate-50 dark:bg-slate-900">
            <Card className="w-full max-w-md shadow-lg">
                <CardHeader className="space-y-1">
                    <CardTitle className="text-2xl font-bold text-center">Forgot Password</CardTitle>
                    <CardDescription className="text-center">
                        Enter your email address and we'll send you a reset token
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="email">Email</Label>
                            <Input
                                id="email"
                                type="email"
                                placeholder="m@example.com"
                                {...register('email')}
                            />
                            {errors.email && (
                                <p className="text-sm text-red-500">{errors.email.message}</p>
                            )}
                        </div>
                        <Button type="submit" className="w-full" disabled={loading}>
                            {loading ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    Sending...
                                </>
                            ) : (
                                'Send Reset Token'
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
