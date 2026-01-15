'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';

import api from '@/lib/axios';
import { Button } from '@/components/ui/button';
import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
    CardDescription
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

const schema = z.object({
    current_password: z.string().min(1, 'Current password is required'),
    new_password: z.string().min(6, 'Password must be at least 6 characters'),
    confirm_password: z.string().min(1, 'Please confirm your password'),
}).refine((data) => data.new_password === data.confirm_password, {
    message: "Passwords don't match",
    path: ["confirm_password"],
});

type FormValues = z.infer<typeof schema>;

export default function ChangePasswordForm() {
    const [isLoading, setIsLoading] = useState(false);

    const {
        register,
        handleSubmit,
        reset,
        formState: { errors }
    } = useForm<FormValues>({
        resolver: zodResolver(schema),
    });

    const onSubmit = async (data: FormValues) => {
        setIsLoading(true);
        try {
            await api.post('/auth/change-password', {
                current_password: data.current_password,
                new_password: data.new_password
            });
            toast.success('Password updated successfully');
            reset();
        } catch (error: any) {
            toast.error(error.response?.data?.detail || 'Failed to update password');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Card>
            <CardHeader>
                <CardTitle>Security</CardTitle>
                <CardDescription>Update your password</CardDescription>
            </CardHeader>
            <CardContent>
                <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                    <div className="space-y-2">
                        <Label htmlFor="current">Current Password</Label>
                        <Input
                            id="current"
                            type="password"
                            {...register('current_password')}
                        />
                        {errors.current_password && (
                            <p className="text-red-500 text-xs">{errors.current_password.message}</p>
                        )}
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="new">New Password</Label>
                        <Input
                            id="new"
                            type="password"
                            {...register('new_password')}
                        />
                        {errors.new_password && (
                            <p className="text-red-500 text-xs">{errors.new_password.message}</p>
                        )}
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="confirm">Confirm New Password</Label>
                        <Input
                            id="confirm"
                            type="password"
                            {...register('confirm_password')}
                        />
                        {errors.confirm_password && (
                            <p className="text-red-500 text-xs">{errors.confirm_password.message}</p>
                        )}
                    </div>

                    <Button type="submit" className="w-full" disabled={isLoading}>
                        {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        change Password
                    </Button>
                </form>
            </CardContent>
        </Card>
    );
}
