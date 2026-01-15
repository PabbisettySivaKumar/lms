'use client';

import { useAuth } from '@/hooks/useAuth';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import ChangePasswordForm from '@/components/profile/ChangePasswordForm';
import PersonalDetailsForm from '@/components/profile/PersonalDetailsForm';

export default function ProfilePage() {
    const { user, isLoading } = useAuth();

    if (isLoading || !user) {
        return (
            <div className="grid gap-6 md:grid-cols-3">
                <div className="h-96 rounded-xl bg-slate-200 animate-pulse col-span-1" />
                <div className="h-96 rounded-xl bg-slate-200 animate-pulse col-span-1" />
                <div className="h-64 rounded-xl bg-slate-200 animate-pulse col-span-1" />
            </div>
        );
    }

    // Helper to safely render fields
    const infoRow = (label: string, value: any) => (
        <div className="flex flex-col space-y-1 py-2">
            <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">{label}</span>
            <span className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate">
                {value || 'N/A'}
            </span>
        </div>
    );

    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-50">My Profile</h1>

            <div className="grid gap-6 lg:grid-cols-3">
                {/* COLUMN 1: WORK IDENTITY */}
                <Card className="lg:col-span-1 border-t-4 border-t-indigo-500">
                    <CardHeader className="flex flex-col items-center text-center pb-2">
                        <Avatar className="h-24 w-24 mb-4">
                            <AvatarImage src="" /> {/* Placeholder */}
                            <AvatarFallback className="text-2xl bg-indigo-100 text-indigo-700">
                                {user.full_name?.charAt(0) || 'U'}
                            </AvatarFallback>
                        </Avatar>
                        <CardTitle className="text-xl">{user.full_name}</CardTitle>
                        <Badge variant="secondary" className="mt-2 text-xs uppercase">
                            {user.role}
                        </Badge>
                    </CardHeader>
                    <Separator />
                    <CardContent className="space-y-1 pt-6">
                        {infoRow("Employee ID", user.employee_id)}
                        {infoRow("Email Address", user.email)}
                        {infoRow("Employee Type", user.employee_type)}
                        {infoRow("Reporting Manager", user.manager_name || user.manager_id)}
                        {infoRow("Joining Date", user.joining_date)}
                    </CardContent>
                </Card>

                {/* COLUMN 2: PERSONAL DETAILS (EDITABLE) */}
                <div className="lg:col-span-1">
                    <PersonalDetailsForm />
                </div>

                {/* COLUMN 3: SECURITY */}
                <div className="lg:col-span-1 space-y-6">
                    <ChangePasswordForm />
                </div>

            </div>
        </div>
    );
}
