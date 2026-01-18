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
import { Badge } from '@/components/ui/badge';

interface LeaveRequest {
    id: string;
    start_date: string;
    end_date: string;
    type: string;
    status: string;
    deductible_days: number;
}

export default function MyLeavesPage() {
    const queryClient = useQueryClient();
    const [leaveToCancel, setLeaveToCancel] = useState<string | null>(null);

    // Fetch Leaves
    const { data: leaves, isLoading } = useQuery({
        queryKey: ['my-leaves'],
        queryFn: async () => {
            const res = await api.get<LeaveRequest[]>('/leaves/mine');
            return res.data;
        },
    });

    // Cancel Mutation
    const cancelMutation = useMutation({
        mutationFn: async (id: string) => {
            const res = await api.post(`/leaves/${id}/cancel`);
            return res.data;
        },
        onSuccess: (data) => {
            toast.success(data.message || 'Leave cancelled successfully');
            queryClient.invalidateQueries({ queryKey: ['my-leaves'] });
            setLeaveToCancel(null);
        },
        onError: (error: any) => {
            toast.error(error.response?.data?.detail || 'Failed to cancel leave');
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
                                        {leave.type.replace('_', ' ')}
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
                                                onClick={() => handleCancelClick(leave.id)}
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

function StatusBadge({ status }: { status: string }) {
    let variant: "default" | "secondary" | "destructive" | "outline" = "outline";
    let className = "";

    switch (status) {
        case 'APPROVED':
            variant = "default";
            className = "bg-green-100 text-green-800 hover:bg-green-100 border-green-200";
            break;
        case 'PENDING':
            variant = "secondary";
            className = "bg-yellow-100 text-yellow-800 hover:bg-yellow-100 border-yellow-200";
            break;
        case 'REJECTED':
            variant = "destructive";
            className = "bg-red-100 text-red-800 hover:bg-red-100 border-red-200";
            break;
        case 'CANCELLED':
            variant = "outline";
            className = "bg-gray-100 text-gray-800 border-gray-200";
            break;
        case 'CANCELLATION_REQUESTED':
            variant = "secondary";
            className = "bg-orange-100 text-orange-800 hover:bg-orange-100 border-orange-200";
            break;
    }

    return (
        <Badge variant={variant} className={className}>
            {status.replace('_', ' ')}
        </Badge>
    );
}
