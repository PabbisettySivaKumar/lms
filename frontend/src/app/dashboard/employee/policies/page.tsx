'use client';

import { useQuery } from '@tanstack/react-query';
import { Loader2, FileText, Download, ExternalLink } from 'lucide-react';
import { format } from 'date-fns';

import api from '@/lib/axios';
import { Button } from '@/components/ui/button';
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
    CardFooter,
} from '@/components/ui/card';

interface LeavePolicy {
    year: number;
    casual_leave_quota: number;
    sick_leave_quota: number;
    wfh_quota: number;
    is_active: boolean;
    _id?: string;
    document_url?: string;
}

export default function EmployeePoliciesPage() {
    // Fetch Active Policy
    const { data: policy, isLoading, isError } = useQuery({
        queryKey: ['active-policy'],
        queryFn: async () => {
            const res = await api.get<LeavePolicy>('/policies/active');
            return res.data;
        },
    });

    if (isLoading) {
        return (
            <div className="flex justify-center p-8">
                <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
            </div>
        );
    }

    if (isError) {
        return (
            <div className="p-8 text-center text-red-500">
                Failed to load policy. Please try again later.
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-50">Company Policies</h1>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                    Latest leave policy and guidelines.
                </p>
            </div>

            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                {!policy || !policy.document_url ? (
                    <div className="col-span-full text-center py-10 text-slate-500 bg-slate-50 rounded-lg border border-dashed">
                        No policy document has been uploaded for {policy?.year || 'this year'}.
                    </div>
                ) : (
                    <Card className="flex flex-col border-l-4 border-l-blue-500">
                        <CardHeader>
                            <div className="flex justify-between items-start">
                                <div className="p-2 bg-blue-50 rounded-full dark:bg-blue-900/30">
                                    <FileText className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                                </div>
                            </div>
                            <CardTitle className="mt-4">Leave Policy {policy.year}</CardTitle>
                            <CardDescription>
                                Official Leave Policy Document for {policy.year}.
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="flex-1">
                            <ul className="text-sm text-slate-600 space-y-1 mt-2">
                                <li>• Casual Leave Quota: {policy.casual_leave_quota}</li>
                                <li>• Sick Leave Quota: {policy.sick_leave_quota}</li>
                                <li>• WFH Quota: {policy.wfh_quota}</li>
                            </ul>
                        </CardContent>
                        <CardFooter className="pt-4 border-t bg-slate-50/50 dark:bg-slate-900/20">
                            <Button className="w-full" asChild>
                                <a
                                    href={`${process.env.NEXT_PUBLIC_API_URL}${policy.document_url}`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                >
                                    <Download className="w-4 h-4 mr-2" />
                                    Download PDF
                                </a>
                            </Button>
                        </CardFooter>
                    </Card>
                )}
            </div>
        </div>
    );
}
