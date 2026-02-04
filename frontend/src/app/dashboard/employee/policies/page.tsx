'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Loader2, FileText, Download, CheckCircle2, ShieldCheck } from 'lucide-react';
import { format } from 'date-fns';
import { toast } from 'sonner';

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

interface LeavePolicy {
    year: number;
    casual_leave_quota: number;
    sick_leave_quota: number;
    wfh_quota: number;
    is_active: boolean;
    id?: number | string; // Backend returns integer, support both
    _id?: string; // Backward compatibility
    documents?: Array<{
        name: string;
        url: string;
        uploaded_at: string;
    }>;
}

export default function EmployeePoliciesPage() {
    const [isAcknowledging, setIsAcknowledging] = useState(false);

    // Fetch Active Policy
    const { data: policy, isLoading, isError } = useQuery({
        queryKey: ['active-policy'],
        queryFn: async () => {
            const res = await api.get<LeavePolicy>('/policies/active', {
                headers: {
                    'Cache-Control': 'no-cache',
                },
            });
            // Debug: Log the response to see if documents are included
            return res.data;
        },
        staleTime: 0, // Always refetch to see latest documents
        refetchOnWindowFocus: true,
        refetchOnMount: true,
    });

    // Fetch Acknowledgment Status list
    const { data: acknowledgments = [], isLoading: isLoadingAck, refetch: refetchAck } = useQuery({
        queryKey: ['my-acknowledgments', policy?.year],
        queryFn: async () => {
            if (!policy?.year) return [];
            const res = await api.get<any[]>(`/policies/${policy.year}/my-acknowledgments`);
            return res.data;
        },
        enabled: !!policy?.year,
    });

    const handleAcknowledge = async (docUrl: string) => {
        if (!policy?.year) return;
        setIsAcknowledging(true);
        try {
            await api.post(`/policies/${policy.year}/acknowledge?document_url=${encodeURIComponent(docUrl)}`);
            toast.success("Document acknowledged successfully");
            refetchAck();
        } catch (error: any) {
            toast.error("Failed to acknowledge document");
        } finally {
            setIsAcknowledging(false);
        }
    };

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

    const hasDocuments = policy?.documents && policy.documents.length > 0;

    const isAcknowledged = (url: string) => {
        return acknowledgments.some((ack: any) => ack.document_url === url);
    };

    const getAckDate = (url: string) => {
        const ack = acknowledgments.find((ack: any) => ack.document_url === url);
        return ack ? format(new Date(ack.acknowledged_at), 'PPP p') : '';
    };

    return (
        <div className="space-y-8">
            <div className="flex justify-between items-end">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-50">Company Policies</h1>
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                        Official company documents and guidelines for {policy?.year || 'this year'}.
                    </p>
                </div>
            </div>

            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                {!hasDocuments ? (
                    <div className="col-span-full text-center py-10 text-slate-500 bg-slate-50 rounded-lg border border-dashed text-sm">
                        No policy documents have been uploaded for {policy?.year || 'this year'}.
                    </div>
                ) : (
                    <>
                        {/* Render documents from the list */}
                        {policy?.documents?.map((doc, idx) => {
                            const acknowledged = isAcknowledged(doc.url);
                            return (
                                <Card key={idx} className={`flex flex-col border-l-4 transition-all duration-300 ${acknowledged ? 'border-l-green-500 bg-green-50/10' : 'border-l-blue-500 hover:shadow-md'}`}>
                                    <CardHeader>
                                        <div className="flex justify-between items-start">
                                            <div className={`p-2 rounded-full ${acknowledged ? 'bg-green-50 dark:bg-green-900/20' : 'bg-blue-50 dark:bg-blue-900/30'}`}>
                                                {acknowledged ? (
                                                    <CheckCircle2 className="h-6 w-6 text-green-600 dark:text-green-400" />
                                                ) : (
                                                    <FileText className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                                                )}
                                            </div>
                                            {acknowledged && (
                                                <Badge variant="outline" className="text-[10px] text-green-600 border-green-200 bg-green-50">Acknowledged</Badge>
                                            )}
                                        </div>
                                        <CardTitle className="mt-4 text-lg">{doc.name}</CardTitle>
                                        <CardDescription>
                                            Updated: {format(new Date(doc.uploaded_at), 'PPP')}
                                        </CardDescription>
                                    </CardHeader>
                                    <CardContent className="flex-1">
                                        <p className="text-sm text-slate-500">
                                            Official {doc.name} for the year {policy.year}.
                                        </p>
                                        {acknowledged && (
                                            <p className="mt-4 text-[11px] text-green-600 font-medium">
                                                Read on: {getAckDate(doc.url)}
                                            </p>
                                        )}
                                    </CardContent>
                                    <CardFooter className="pt-4 border-t bg-slate-50/50 dark:bg-slate-900/20 flex flex-col gap-2">
                                        <Button className="w-full h-9 text-xs" variant="outline" asChild>
                                            <a
                                                href={`/api${doc.url}`}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                            >
                                                <Download className="w-3.5 h-3.5 mr-2" />
                                                View Document
                                            </a>
                                        </Button>

                                        {!acknowledged && (
                                            <Button
                                                className="w-full h-9 text-xs bg-blue-600 hover:bg-blue-700"
                                                size="sm"
                                                onClick={() => handleAcknowledge(doc.url)}
                                                disabled={isAcknowledging}
                                            >
                                                {isAcknowledging ? (
                                                    <Loader2 className="w-3.5 h-3.5 animate-spin mr-2" />
                                                ) : (
                                                    <ShieldCheck className="w-3.5 h-3.5 mr-2" />
                                                )}
                                                Acknowledge Receipt
                                            </Button>
                                        )}
                                    </CardFooter>
                                </Card>
                            );
                        })}

                    </>
                )}
            </div>
        </div>
    );
}
