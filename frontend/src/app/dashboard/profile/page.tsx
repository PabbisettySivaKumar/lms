'use client';

import { useAuth } from '@/hooks/useAuth';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import ChangePasswordForm from '@/components/profile/ChangePasswordForm';
import PersonalDetailsForm from '@/components/profile/PersonalDetailsForm';
import DocumentsCard from '@/components/profile/DocumentsCard';
import { useState, useRef } from 'react';
import { Camera, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { BACKEND_URL } from '@/lib/config';

export default function ProfilePage() {
    const { user, isLoading, refreshUser } = useAuth();
    const [isUploading, setIsUploading] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        // Basic client-side validation
        if (!file.type.startsWith('image/')) {
            toast.error("Please upload an image file");
            return;
        }

        if (file.size > 5 * 1024 * 1024) { // 5MB limit
            toast.error("Image size must be less than 5MB");
            return;
        }

        try {
            setIsUploading(true);
            const formData = new FormData();
            formData.append('file', file);

            const token = localStorage.getItem('access_token');
            const res = await fetch(`${BACKEND_URL}/users/me/profile-picture`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
                body: formData,
            });

            if (!res.ok) {
                const errorData = await res.json();
                throw new Error(errorData.detail || 'Failed to upload image');
            }

            toast.success("Profile picture updated successfully");
            await refreshUser(); // This will help to update the avatar on sidebar as well if used there
        } catch (error: any) {
            console.error("Upload error:", error);
            toast.error(error.message || "Something went wrong");
        } finally {
            setIsUploading(false);
            if (fileInputRef.current) {
                fileInputRef.current.value = '';
            }
        }
    };

    const triggerFileInput = () => {
        if (!isUploading) {
            fileInputRef.current?.click();
        }
    };


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
            <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-50">Profile</h1>

            <div className="grid gap-6 lg:grid-cols-2">
                {/* COLUMN 1: WORK IDENTITY */}
                <div className="lg:col-span-1 space-y-6">
                    <Card className="border-t-4 border-t-indigo-500">
                        <CardHeader className="flex flex-col items-center text-center pb-2">

                            <div className="relative group cursor-pointer" onClick={triggerFileInput}>
                                <Avatar className="h-24 w-24 mb-4 ring-4 ring-slate-50 dark:ring-slate-800 transition-all group-hover:opacity-90">
                                    <AvatarImage
                                        src={user.profile_picture_url ? `${BACKEND_URL}${user.profile_picture_url}` : ""}
                                        className="object-cover"
                                    />
                                    <AvatarFallback className="text-2xl bg-indigo-100 text-indigo-700">
                                        {user.full_name?.charAt(0) || 'U'}
                                    </AvatarFallback>
                                </Avatar>

                                {/* Overlay */}
                                <div className="absolute inset-0 flex items-center justify-center bg-black/40 rounded-full opacity-0 group-hover:opacity-100 transition-opacity mb-4">
                                    {isUploading ? (
                                        <Loader2 className="h-6 w-6 text-white animate-spin" />
                                    ) : (
                                        <Camera className="h-8 w-8 text-white" />
                                    )}
                                </div>

                                {/* Hidden Input */}
                                <input
                                    type="file"
                                    ref={fileInputRef}
                                    className="hidden"
                                    accept="image/png, image/jpeg, image/jpg"
                                    onChange={handleFileChange}
                                />
                            </div>

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
                            {infoRow("Date of Birth", user.dob)}
                            {infoRow("Joining Date", user.joining_date)}
                            {(() => {
                                if (user.joining_date) {
                                    try {
                                        // Simple manual calculation to avoid heavy imports
                                        const join = new Date(user.joining_date);
                                        const now = new Date();

                                        let years = now.getFullYear() - join.getFullYear();
                                        let months = now.getMonth() - join.getMonth();

                                        if (months < 0) {
                                            years--;
                                            months += 12;
                                        }

                                        const expStr = `${years} Year${years !== 1 ? 's' : ''}, ${months} Month${months !== 1 ? 's' : ''}`;
                                        return infoRow("Experience", expStr);
                                    } catch (e) {
                                        return null;
                                    }
                                }
                                return null;
                            })()}
                        </CardContent>
                    </Card>
                    <DocumentsCard />
                </div>

                {/* COLUMN 2: PERSONAL DETAILS (EDITABLE) */}
                <div className="lg:col-span-1">
                    <PersonalDetailsForm />
                </div>
            </div>
        </div>
    );
}
