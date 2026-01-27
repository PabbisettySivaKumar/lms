'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { format, parseISO } from 'date-fns';
import { toast } from 'sonner';
import { Loader2, AlertCircle } from 'lucide-react';

import api from '@/lib/axios';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import { formatLeaveType } from '@/lib/leaveUtils';
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import { StatusBadge } from '@/components/common/StatusBadge';
import { Pagination } from '@/components/common/Pagination';

interface LeaveRequest {
    id: number | string; // Backend returns integer, but we support both
    _id?: string; // Backward compatibility
    start_date: string;
    end_date: string | null;
    type: string;
    status: string;
    deductible_days: number;
}

export default function MyLeavesPage() {
    const queryClient = useQueryClient();
    const [leaveToCancel, setLeaveToCancel] = useState<string | null>(null);

    // Pagination state
    const [page, setPage] = useState(1);
    const itemsPerPage = 20;

    // Fetch Leaves with pagination
    const { data: leavesData, isLoading } = useQuery({
        queryKey: ['my-leaves', page],
        queryFn: async () => {
            const params = new URLSearchParams({
                skip: String((page - 1) * itemsPerPage),
                limit: String(itemsPerPage),
            });
            const res = await api.get<{
                leaves: LeaveRequest[];
                total: number;
                skip: number;
                limit: number;
            }>(`/leaves/mine?${params.toString()}`);
            return res.data;
        },
    });

    const leaves = leavesData?.leaves || [];
    const totalLeaves = leavesData?.total || 0;
    const totalPages = Math.ceil(totalLeaves / itemsPerPage);

    // Cancel Mutation
    const cancelMutation = useMutation({
        mutationFn: async (id: number | string) => {
            // Backend accepts string IDs in URL and converts to integer
            const res = await api.post(`/leaves/${String(id)}/cancel`);
            return res.data;
        },
        onSuccess: (data) => {
            toast.success(data.message || 'Leave cancelled successfully');
            queryClient.invalidateQueries({ queryKey: ['my-leaves'] });
            setLeaveToCancel(null);
        },
        onError: (error: any) => {
            // Better error handling
            let errorMessage = 'Failed to cancel leave';
            
            if (error.response) {
                // Server responded with error
                errorMessage = error.response.data?.detail || 
                              error.response.data?.message || 
                              error.response.statusText || 
                              `Server error (${error.response.status})`;
            } else if (error.request) {
                // Request made but no response
                errorMessage = 'No response from server. Please check if the backend is running.';
            } else {
                // Error setting up request
                errorMessage = error.message || 'Request failed';
            }
            
            toast.error(errorMessage);
        },
    });

    const handleCancelClick = (id: string) => {
        setLeaveToCancel(id);
    };

    const handleConfirmCancel = () => {
        if (leaveToCancel) {
            cancelMutation.mutate(leaveToCancel);
        }
    };

    if (isLoading) {
        return (
            <div className="flex h-[50vh] items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-3xl font-bold tracking-tight">Leaves</h1>
            </div>

            <div className="rounded-md border bg-white dark:bg-slate-950">
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Type</TableHead>
                            <TableHead>Start Date</TableHead>
                            <TableHead>End Date</TableHead>
                            <TableHead>Days</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead className="text-right">Actions</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {leaves?.length === 0 ? (
                            <TableRow>
                                <TableCell colSpan={6} className="h-24 text-center">
                                    No leave requests found.
                                </TableCell>
                            </TableRow>
                        ) : (
                            leaves?.map((leave) => (
                                <TableRow key={leave.id}>
                                    <TableCell className="font-medium">
                                        {formatLeaveType(leave.type)}
                                    </TableCell>
                                    <TableCell>
                                        {format(parseISO(leave.start_date), 'MMM d, yyyy')}
                                    </TableCell>
                                    <TableCell>
                                        {leave.end_date
                                            ? format(parseISO(leave.end_date), 'MMM d, yyyy')
                                            : <span className="text-slate-500 italic">Indefinite</span>
                                        }
                                    </TableCell>
                                    <TableCell>{leave.deductible_days}</TableCell>
                                    <TableCell>
                                        <StatusBadge status={leave.status} />
                                    </TableCell>
                                    <TableCell className="text-right">
                                        {['PENDING', 'APPROVED'].includes(leave.status) && (
                                            <Button
                                                variant="destructive"
                                                size="sm"
                                                onClick={() => handleCancelClick(String(leave.id))}
                                                disabled={cancelMutation.isPending}
                                            >
                                                Cancel
                                            </Button>
                                        )}
                                    </TableCell>
                                </TableRow>
                            ))
                        )}
                    </TableBody>
                </Table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
                <Pagination
                    currentPage={page}
                    totalPages={totalPages}
                    onPageChange={setPage}
                    totalItems={totalLeaves}
                    itemsPerPage={itemsPerPage}
                />
            )}

            <AlertDialog open={!!leaveToCancel} onOpenChange={(open) => !open && setLeaveToCancel(null)}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Are you sure?</AlertDialogTitle>
                        <AlertDialogDescription>
                            This action will withdraw your leave request. If it was already approved,
                            it may require manager approval to cancel.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Dismiss</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={handleConfirmCancel}
                            className="bg-red-600 hover:bg-red-700 focus:ring-red-600"
                        >
                            {cancelMutation.isPending ? 'Cancelling...' : 'Confirm Cancellation'}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
}
