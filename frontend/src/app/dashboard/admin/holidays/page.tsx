'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Trash2, Calendar as CalendarIcon, Upload } from 'lucide-react';
import { format, parseISO } from 'date-fns';
import { toast } from 'sonner';

import api from '@/lib/axios';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/button';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import { Card, CardContent } from '@/components/ui/card';
import { AddHolidayDialog } from '@/components/admin/AddHolidayDialog';

interface Holiday {
    id: number | string; // Backend returns integer, support both
    _id?: string; // Backward compatibility
    name: string;
    date: string;
    is_optional: boolean;
}

import { ImportHolidaysDialog } from '@/components/admin/ImportHolidaysDialog';

export default function AdminHolidaysPage() {
    const { user, isLoading } = useAuth();
    const router = useRouter();
    const queryClient = useQueryClient();
    const [isAddOpen, setIsAddOpen] = useState(false);
    const [isImportOpen, setIsImportOpen] = useState(false);

    // Access check
    useEffect(() => {
        if (!isLoading && user) {
            const allowed = ['admin', 'hr', 'founder'];
            if (!allowed.includes(user.role)) {
                router.push('/dashboard');
            }
        }
    }, [user, isLoading, router]);

    // Fetch Holidays
    const { data: holidays, isLoading: holidaysLoading, refetch: refetchHolidays } = useQuery({
        queryKey: ['holidays'],
        queryFn: async () => {
            try {
                const res = await api.get<any[]>('/calendar/holidays', {
                    headers: {
                        'Cache-Control': 'no-cache'
                    }
                });
                console.log('Fetched Holidays:', res.data, 'Count:', res.data?.length);
                const mapped = res.data.map((h: any) => ({
                    ...h,
                    id: h.id // Backend returns integer ID
                })) as Holiday[];
                console.log('Mapped Holidays:', mapped);
                return mapped;
            } catch (e) {
                console.error('Error fetching holidays:', e);
                return [];
            }
        },
        enabled: !!user,
        staleTime: 0, // Always consider data stale to allow immediate refetch after invalidation
        refetchOnWindowFocus: true, // Refetch when window regains focus
        refetchOnMount: true, // Always refetch when component mounts
    });

    // Delete Mutation
    const deleteMutation = useMutation({
        mutationFn: async (id: number | string) => {
            // Backend accepts string IDs in URL and converts to integer
            await api.delete(`/admin/holidays/${String(id)}`);
        },
        onSuccess: () => {
            toast.success('Holiday deleted');
            // Invalidate and refetch immediately
            queryClient.invalidateQueries({ queryKey: ['holidays'], refetchType: 'active' });
            queryClient.invalidateQueries({ queryKey: ['calendar-holidays'], refetchType: 'active' });
            queryClient.refetchQueries({ queryKey: ['holidays'] });
        },
        onError: (error: any) => {
            toast.error(error.response?.data?.detail || 'Failed to delete holiday');
        }
    });

    const handleDelete = (id: number | string) => {
        if (confirm('Are you sure you want to delete this holiday?')) {
            deleteMutation.mutate(id);
        }
    }

    const handleYearlyReset = async () => {
        if (confirm('⚠️ WARNING: This will RESET all employee leave balances (CL=0, SL=Quota, EL=50% Carry). Are you sure?')) {
            try {
                await api.post('/admin/yearly-reset');
                toast.success('Yearly leave reset completed successfully.');
            } catch (error: any) {
                toast.error(error.response?.data?.message || 'Failed to reset leaves.');
            }
        }
    }

    if (isLoading || holidaysLoading) return <div className="p-8">Loading holidays...</div>;

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-3xl font-bold tracking-tight">Holiday Planner</h1>
                <div className="flex gap-2">
                    <Button variant="destructive" onClick={handleYearlyReset}>
                        ⚠️ Reset Leaves (Manual)
                    </Button>
                    <Button 
                        variant="outline" 
                        onClick={() => refetchHolidays()}
                        disabled={holidaysLoading}
                    >
                        {holidaysLoading ? 'Refreshing...' : 'Refresh'}
                    </Button>
                    <Button variant="outline" onClick={() => setIsImportOpen(true)}>
                        <Upload className="mr-2 h-4 w-4" /> Import CSV
                    </Button>
                    <Button onClick={() => setIsAddOpen(true)}>
                        <Plus className="mr-2 h-4 w-4" /> Add Holiday
                    </Button>
                </div>
            </div>

            <Card>
                <CardContent className="p-0">
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Date</TableHead>
                                <TableHead>Holiday Name</TableHead>
                                <TableHead>Type</TableHead>
                                <TableHead className="text-right">Actions</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {(!holidays || holidays.length === 0) && !holidaysLoading ? (
                                <TableRow>
                                    <TableCell colSpan={4} className="text-center py-8 text-slate-500">
                                        No holidays found. Add one to get started.
                                    </TableCell>
                                </TableRow>
                            ) : (
                                holidays?.map((h, i) => (
                                    <TableRow key={h.id || i}>
                                        <TableCell className="font-medium flex items-center">
                                            <CalendarIcon className="mr-2 h-4 w-4 text-slate-500" />
                                            {format(parseISO(h.date), 'PPP')}
                                        </TableCell>
                                        <TableCell>{h.name}</TableCell>
                                        <TableCell>
                                            {h.is_optional ? (
                                                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
                                                    Optional
                                                </span>
                                            ) : (
                                                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-700">
                                                    Public
                                                </span>
                                            )}
                                        </TableCell>
                                        <TableCell className="text-right">
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                className="text-red-600 hover:text-red-700 hover:bg-red-50"
                                                onClick={() => handleDelete(String(h.id))}
                                                disabled={deleteMutation.isPending}
                                            >
                                                <Trash2 className="h-4 w-4" />
                                            </Button>
                                        </TableCell>
                                    </TableRow>
                                ))
                            )}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>

            <AddHolidayDialog
                isOpen={isAddOpen}
                onClose={() => setIsAddOpen(false)}
            />

            <ImportHolidaysDialog
                isOpen={isImportOpen}
                onClose={() => setIsImportOpen(false)}
            />
        </div>
    );
}
