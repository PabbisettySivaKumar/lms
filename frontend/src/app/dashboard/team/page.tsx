'use client';

import { useEffect, useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Check, X, Loader2, UserCheck, UserX } from 'lucide-react';

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
import { formatLeaveType } from '@/lib/leaveUtils';
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
  id: number | string; // Backend returns integer, support both
  _id?: string; // Backward compatibility
  applicant_name: string;
  type: string;
  start_date: string;
  end_date: string | null;
  deductible_days: number;
  reason: string;
}

interface TeamMember {
  id: number | string;
  employee_id: string;
  full_name: string;
  email: string;
  role?: string;
  casual_balance?: number;
  sick_balance?: number;
  earned_balance?: number;
  comp_off_balance?: number;
  wfh_balance?: number;
}

interface TeamPresenceMember {
  id: number;
  employee_id: string;
  full_name: string;
  email: string;
  presence_status: 'present' | 'on_leave';
  leave_type?: string | null;
  leave_start_date?: string | null;
  leave_end_date?: string | null;
  date: string;
}

export default function TeamPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const queryClient = useQueryClient();

  // Dialog State
  const [rejectDialog, setRejectDialog] = useState<{ isOpen: boolean; id: number | string | null }>({
    isOpen: false,
    id: null,
  });
  const [rejectReason, setRejectReason] = useState('');

  // Team presence date (default: today)
  const todayStr = useMemo(() => new Date().toISOString().slice(0, 10), []);
  const [presenceDate, setPresenceDate] = useState(todayStr);

  // Manager+ can see pending requests, full team, and presence. Employees see only teammates (peers under same manager).
  const canSeeTeam = !!user && ['manager', 'hr', 'founder', 'co_founder', 'admin'].includes(user.role ?? '');
  const isEmployeeRole = !!user && ['employee', 'intern', 'contract'].includes(user.role ?? '');

  // Fetch Data — pending leaves (for manager+ only; employees get empty list from API)
  const { data, isLoading: isDataLoading } = useQuery({
    queryKey: ['pending-leaves'],
    queryFn: async () => {
      const res = await api.get<{ leaves: LeaveRequest[]; comp_offs: LeaveRequest[] }>('/leaves/pending');
      return [...res.data.leaves, ...res.data.comp_offs];
    },
    enabled: !!user && canSeeTeam,
  });

  // Team roster (GET /manager/team) — manager+ only
  const { data: teamRoster, isLoading: isTeamRosterLoading } = useQuery({
    queryKey: ['manager-team'],
    queryFn: async () => {
      const res = await api.get<TeamMember[]>('/manager/team');
      return res.data;
    },
    enabled: canSeeTeam,
  });

  // Teammates (GET /manager/team/peers) — employees: others under the same manager
  const { data: teamPeers, isLoading: isTeamPeersLoading } = useQuery({
    queryKey: ['manager-team-peers'],
    queryFn: async () => {
      const res = await api.get<TeamMember[]>('/manager/team/peers');
      return res.data;
    },
    enabled: isEmployeeRole,
  });

  // Team presence for selected date — manager+ only
  const { data: presenceData, isLoading: isPresenceLoading } = useQuery({
    queryKey: ['manager-team-presence', presenceDate],
    queryFn: async () => {
      const res = await api.get<TeamPresenceMember[]>(`/manager/team/presence?date=${presenceDate}`);
      return res.data;
    },
    enabled: canSeeTeam && !!presenceDate,
  });

  // Actions
  const actionMutation = useMutation({
    mutationFn: async ({ id, action, note }: { id: number | string; action: 'APPROVE' | 'REJECT'; note?: string }) => {
      // Backend accepts string IDs in URL and converts to integer
      await api.patch(`/leaves/action/${String(id)}`, null, {
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

  const handleApprove = (id: string | number) => {
    actionMutation.mutate({ id: String(id), action: 'APPROVE' });
  };

  const handleRejectClick = (id: string | number) => {
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

  if (isLoading) {
    return <div className="p-8">Loading…</div>;
  }
  if (canSeeTeam && isDataLoading) {
    return <div className="p-8">Loading team…</div>;
  }

  const showPresence = canSeeTeam;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">
          {canSeeTeam ? 'Team Approvals' : 'My Teammates'}
        </h1>
      </div>

      {/* Pending leave/comp-off requests — manager+ only */}
      {canSeeTeam && (
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
                          {formatLeaveType(req.type)}
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
      )}

      {/* My Teammates (GET /manager/team/peers) — employees: others under the same manager */}
      {isEmployeeRole && (
        <Card>
          <CardHeader>
            <CardTitle>My Teammates</CardTitle>
            <p className="text-sm text-muted-foreground">
              Colleagues who report to the same manager as you.
            </p>
          </CardHeader>
          <CardContent>
            {isTeamPeersLoading ? (
              <div className="flex justify-center py-8 text-muted-foreground">
                <Loader2 className="h-6 w-6 animate-spin" />
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Employee ID</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Role</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {!teamPeers?.length ? (
                    <TableRow>
                      <TableCell colSpan={4} className="h-24 text-center text-muted-foreground">
                        No teammates found. You may have no manager assigned, or you are the only one under your manager.
                      </TableCell>
                    </TableRow>
                  ) : (
                    teamPeers.map((member) => (
                      <TableRow key={member.id}>
                        <TableCell className="font-medium">{member.full_name}</TableCell>
                        <TableCell>{member.employee_id}</TableCell>
                        <TableCell className="max-w-[200px] truncate" title={member.email}>{member.email}</TableCell>
                        <TableCell className="capitalize">{member.role ?? '—'}</TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}

      {/* My Team roster (GET /manager/team) */}
      {showPresence && (
        <Card>
          <CardHeader>
            <CardTitle>My Team</CardTitle>
            <p className="text-sm text-muted-foreground">
              {user?.role === 'manager' ? 'Your direct reports.' : 'All active users (HR/Admin/Founder/Co-founder view).'}
            </p>
          </CardHeader>
          <CardContent>
            {isTeamRosterLoading ? (
              <div className="flex justify-center py-8 text-muted-foreground">
                <Loader2 className="h-6 w-6 animate-spin" />
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Employee ID</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead className="text-right">CL</TableHead>
                    <TableHead className="text-right">SL</TableHead>
                    <TableHead className="text-right">EL</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {!teamRoster?.length ? (
                    <TableRow>
                      <TableCell colSpan={7} className="h-24 text-center text-muted-foreground">
                        No team members. {user?.role === 'manager' ? 'Assign direct reports in Admin → Users.' : ''}
                      </TableCell>
                    </TableRow>
                  ) : (
                    teamRoster.map((member) => (
                      <TableRow key={member.id}>
                        <TableCell className="font-medium">{member.full_name}</TableCell>
                        <TableCell>{member.employee_id}</TableCell>
                        <TableCell className="max-w-[200px] truncate" title={member.email}>{member.email}</TableCell>
                        <TableCell className="capitalize">{member.role ?? '—'}</TableCell>
                        <TableCell className="text-right">{member.casual_balance ?? 0}</TableCell>
                        <TableCell className="text-right">{member.sick_balance ?? 0}</TableCell>
                        <TableCell className="text-right">{member.earned_balance ?? 0}</TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}

      {/* Team presence: who is present / on leave on a given day */}
      {showPresence && (
        <Card>
          <CardHeader>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <CardTitle>Team presence</CardTitle>
              <div className="flex items-center gap-2">
                <Label htmlFor="presence-date" className="text-sm text-muted-foreground whitespace-nowrap">
                  Date
                </Label>
                <Input
                  id="presence-date"
                  type="date"
                  value={presenceDate}
                  onChange={(e) => setPresenceDate(e.target.value)}
                  className="w-[160px]"
                />
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {isPresenceLoading ? (
              <div className="flex items-center justify-center py-8 text-muted-foreground">
                <Loader2 className="h-6 w-6 animate-spin mr-2" />
                Loading presence…
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Employee ID</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Leave (if on leave)</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {!presenceData?.length ? (
                    <TableRow>
                      <TableCell colSpan={4} className="h-24 text-center text-muted-foreground">
                        No direct reports, or they are not assigned to you as manager.
                      </TableCell>
                    </TableRow>
                  ) : (
                    presenceData.map((member) => (
                      <TableRow key={member.id}>
                        <TableCell className="font-medium">{member.full_name}</TableCell>
                        <TableCell>{member.employee_id}</TableCell>
                        <TableCell>
                          {member.presence_status === 'present' ? (
                            <span className="inline-flex items-center gap-1.5 text-emerald-600">
                              <UserCheck className="h-4 w-4" />
                              Present
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1.5 text-amber-600">
                              <UserX className="h-4 w-4" />
                              On leave
                            </span>
                          )}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {member.presence_status === 'on_leave' && member.leave_type ? (
                            <>
                              {formatLeaveType(member.leave_type)}
                              {member.leave_start_date && member.leave_end_date && (
                                <span className="ml-2 text-xs">
                                  ({member.leave_start_date === member.leave_end_date
                                    ? member.leave_start_date
                                    : `${member.leave_start_date} – ${member.leave_end_date}`})
                                </span>
                              )}
                            </>
                          ) : (
                            '—'
                          )}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}

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
