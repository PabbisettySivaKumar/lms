'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Check, X, Loader2 } from 'lucide-react';

import api from '@/lib/axios';
import { useAuth } from '@/hooks/useAuth';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface LeaveRequest {
  id: string;
  applicant_name: string;
  type: string;
  start_date: string;
  end_date: string;
  deductible_days: number;
  reason: string;
}

export default function TeamPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const queryClient = useQueryClient();

  // Dialog State
  const [rejectDialog, setRejectDialog] = useState<{ isOpen: boolean; id: string | null }>({
    isOpen: false,
    id: null,
  });
  const [rejectReason, setRejectReason] = useState('');

  // Access Control
  useEffect(() => {
    if (!isLoading && user) {
      const allowed = ['manager', 'hr', 'founder', 'admin'];
      if (!allowed.includes(user.role)) {
        router.push('/dashboard');
      }
    }
  }, [user, isLoading, router]);

  // Fetch Data
  const { data, isLoading: isDataLoading } = useQuery({
    queryKey: ['pending-leaves'],
    queryFn: async () => {
      const res = await api.get<{ leaves: LeaveRequest[]; comp_offs: LeaveRequest[] }>('/leaves/pending');
      // Normalize: Combine both lists
      return [...res.data.leaves, ...res.data.comp_offs];
    },
    enabled: !!user,
  });

  // Actions
  const actionMutation = useMutation({
    mutationFn: async ({ id, action, note }: { id: string; action: 'APPROVE' | 'REJECT'; note?: string }) => {
      await api.patch(`/leaves/action/${id}`, null, {
        params: { action, note }
      });
    },
    onSuccess: () => {
      toast.success('Action processed successfully');
      queryClient.invalidateQueries({ queryKey: ['pending-leaves'] });
      setRejectDialog({ isOpen: false, id: null });
      setRejectReason('');
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || 'Action failed');
    }
  });

  const handleApprove = (id: string) => {
    actionMutation.mutate({ id, action: 'APPROVE' });
  };

  const handleRejectClick = (id: string) => {
    setRejectDialog({ isOpen: true, id });
  };

  const confirmReject = () => {
    if (!rejectReason.trim()) {
      toast.error('Rejection reason is required');
      return;
    }
    if (rejectDialog.id) {
      actionMutation.mutate({ id: rejectDialog.id, action: 'REJECT', note: rejectReason });
    }
  };

  if (isLoading || isDataLoading) {
    return <div className="p-8">Loading team properties...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Team Approvals</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Pending Requests</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Employee</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Dates</TableHead>
                <TableHead>Days</TableHead>
                <TableHead>Reason</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data?.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="h-24 text-center">
                    No pending requests.
                  </TableCell>
                </TableRow>
              ) : (
                data?.map((req) => (
                  <TableRow key={req.id}>
                    <TableCell className="font-medium">{req.applicant_name}</TableCell>
                    <TableCell>
                      {req.type === 'COMP_OFF_GRANT' ? (
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-purple-50 text-purple-700 border border-purple-200">
                          Grant Request
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-700">
                          {req.type}
                        </span>
                      )}
                    </TableCell>
                    <TableCell>
                      {req.start_date === req.end_date
                        ? req.start_date
                        : `${req.start_date} - ${req.end_date}`}
                    </TableCell>
                    <TableCell>{req.deductible_days}</TableCell>
                    <TableCell className="max-w-[200px] truncate" title={req.reason}>
                      {req.reason}
                    </TableCell>
                    <TableCell className="text-right space-x-2">
                      <Button
                        size="sm"
                        variant="ghost"
                        className="text-green-600 hover:text-green-700 hover:bg-green-50"
                        onClick={() => handleApprove(req.id)}
                      >
                        <Check className="h-4 w-4" />
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="text-red-600 hover:text-red-700 hover:bg-red-50"
                        onClick={() => handleRejectClick(req.id)}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Rejection Dialog */}
      <Dialog open={rejectDialog.isOpen} onOpenChange={(open) => !open && setRejectDialog({ isOpen: false, id: null })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reject Request</DialogTitle>
            <DialogDescription>
              Please provide a reason for rejecting this leave request.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="reason">Reason</Label>
              <Input
                id="reason"
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="e.g., Critical project delivery..."
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRejectDialog({ isOpen: false, id: null })}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={confirmReject} disabled={actionMutation.isPending}>
              {actionMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Confirm Rejection
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
