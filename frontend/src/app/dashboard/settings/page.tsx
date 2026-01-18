'use client';

import { useAuth } from '@/hooks/useAuth';
import ChangePasswordForm from '@/components/profile/ChangePasswordForm';

export default function SettingsPage() {
    const { user, isLoading } = useAuth();

    if (isLoading || !user) {
        return (
            <div className="h-96 rounded-xl bg-slate-200 animate-pulse" />
        );
    }

    return (
        <div className="space-y-6 max-w-4xl mx-auto">
            <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-50">Settings</h1>

            <div className="space-y-6">
                <div className="grid gap-6">
                    {/* Security Section */}
                    <div className="space-y-4">
                        <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50">Security</h2>
                        <div className="max-w-xl">
                            <ChangePasswordForm />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
