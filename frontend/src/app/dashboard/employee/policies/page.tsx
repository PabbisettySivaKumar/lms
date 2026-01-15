'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Loader2, FileText, CheckCircle2, AlertCircle, ExternalLink } from 'lucide-react';
import { toast } from 'sonner';
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
import { Badge } from '@/components/ui/badge';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from '@/components/ui/dialog';
import { useState } from 'react';

interface Policy {
    _id: string;
    title: string;
    file_url: string;
    created_at: string;
    is_acknowledged: boolean;
    acknowledged_at?: string;
}

export default function EmployeePoliciesPage() {
    const queryClient = useQueryClient();
    const [selectedPolicy, setSelectedPolicy] = useState<Policy | null>(null);

    // Fetch Policies
    const { data: policies, isLoading } = useQuery({
        queryKey: ['policies'],
        queryFn: async () => {
            const res = await api.get<Policy[]>('/policies');
            return res.data;
        },
    });

    // Acknowledge Mutation
    const acknowledgeMutation = useMutation({
        mutationFn: async (id: string) => {
            await api.post(`/policies/${id}/acknowledge`);
        },
        onSuccess: () => {
            toast.success('Policy acknowledged successfully');
            queryClient.invalidateQueries({ queryKey: ['policies'] });
            setSelectedPolicy(null);
        },
        onError: () => {
            toast.error('Failed to acknowledge policy');
        },
    });

    const handleAcknowledge = () => {
        if (selectedPolicy) {
            acknowledgeMutation.mutate(selectedPolicy._id);
        }
    };

    if (isLoading) {
        return (
            <div className="flex justify-center p-8">
                <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-50">Company Policies</h1>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                    Review and acknowledge updated company policies.
                </p>
            </div>

            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                {policies?.length === 0 ? (
                    <div className="col-span-full text-center py-10 text-slate-500 bg-slate-50 rounded-lg border border-dashed">
                        No policies available at this time.
                    </div>
                ) : (
                    policies?.map((policy) => (
                        <Card key={policy._id} className="flex flex-col">
                            <CardHeader>
                                <div className="flex justify-between items-start">
                                    <div className="p-2 bg-slate-100 rounded-full dark:bg-slate-800">
                                        <FileText className="h-6 w-6 text-slate-600 dark:text-slate-400" />
                                    </div>
                                    {policy.is_acknowledged ? (
                                        <Badge variant="secondary" className="bg-emerald-100 text-emerald-800 hover:bg-emerald-100 dark:bg-emerald-900/30 dark:text-emerald-400 border-emerald-200">
                                            <CheckCircle2 className="w-3 h-3 mr-1" />
                                            Signed
                                        </Badge>
                                    ) : (
                                        <Badge variant="secondary" className="bg-amber-100 text-amber-800 hover:bg-amber-100 dark:bg-amber-900/30 dark:text-amber-400 border-amber-200">
                                            <AlertCircle className="w-3 h-3 mr-1" />
                                            Action Required
                                        </Badge>
                                    )}
                                </div>
                                <CardTitle className="mt-4 break-words">{policy.title}</CardTitle>
                                <CardDescription>
                                    Published on {format(new Date(policy.created_at), 'PPP')}
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="flex-1">
                                {policy.is_acknowledged && (
                                    <p className="text-xs text-slate-500 mt-2">
                                        Acknowledged on {format(new Date(policy.acknowledged_at!), 'PPP p')}
                                    </p>
                                )}
                            </CardContent>
                            <CardFooter className="pt-2 gap-2 border-t bg-slate-50/50 dark:bg-slate-900/20">
                                <Button variant="outline" className="w-full" asChild>
                                    <a
                                        href={`${process.env.NEXT_PUBLIC_API_URL}${policy.file_url}`}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                    >
                                        <ExternalLink className="w-4 h-4 mr-2" />
                                        View PDF
                                    </a>
                                </Button>
                                {!policy.is_acknowledged && (
                                    <Dialog>
                                        <DialogTrigger asChild>
                                            <Button className="w-full" onClick={() => setSelectedPolicy(policy)}>
                                                Acknowledge
                                            </Button>
                                        </DialogTrigger>
                                        <DialogContent>
                                            <DialogHeader>
                                                <DialogTitle>Acknowledge Policy</DialogTitle>
                                                <DialogDescription>
                                                    Please confirm you have read the document.
                                                </DialogDescription>
                                            </DialogHeader>
                                            <div className="py-4">
                                                <h4 className="font-semibold mb-2">{policy.title}</h4>
                                                <p className="text-sm text-slate-600 mb-4">
                                                    By clicking "I Confirm", you acknowledge that you have read, understood, and agree to abide by the terms set forth in this policy document.
                                                </p>
                                                <div className="flex flex-col gap-2">
                                                    <Button variant="outline" asChild>
                                                        <a
                                                            href={`${process.env.NEXT_PUBLIC_API_URL}${policy.file_url}`}
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            className="w-full justify-center"
                                                        >
                                                            <ExternalLink className="w-4 h-4 mr-2" />
                                                            Open Document First
                                                        </a>
                                                    </Button>
                                                </div>
                                            </div>
                                            <DialogFooter>
                                                <Button onClick={handleAcknowledge} disabled={acknowledgeMutation.isPending}>
                                                    {acknowledgeMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                                    I Confirm
                                                </Button>
                                            </DialogFooter>
                                        </DialogContent>
                                    </Dialog>
                                )}
                            </CardFooter>
                        </Card>
                    ))
                )}
            </div>
        </div>
    );
}
