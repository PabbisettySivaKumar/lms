'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { Plus, Edit2, MoreVertical, Trash, UserCog, CreditCard, Loader2 } from 'lucide-react';
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
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { AddUserDialog } from '@/components/admin/AddUserDialog';
import { EditBalanceDialog } from '@/components/admin/EditBalanceDialog';
import EditUserDialog from '@/components/admin/EditUserDialog';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
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

interface UserData {
    id: string; // From _id
    employee_id: string;
    full_name: string;
    email: string;
    role: string;
    manager_id?: string;
    casual_balance: number;
    sick_balance: number;
    earned_balance: number;
    comp_off_balance: number;
}

interface ManagerData {
    full_name: string;
    employee_id: string;
    email: string;
}

export default function AdminUsersPage() {
    const { user, isLoading } = useAuth();
    const router = useRouter();

    const [isAddOpen, setIsAddOpen] = useState(false);
    const [editingBalanceUser, setEditingBalanceUser] = useState<UserData | null>(null);
    const [editingDetailsUser, setEditingDetailsUser] = useState<UserData | null>(null);
    const [deletingUser, setDeletingUser] = useState<UserData | null>(null);

    // Access check
    useEffect(() => {
        if (!isLoading && user) {
            const allowed = ['admin', 'hr', 'founder'];
            if (!allowed.includes(user.role)) {
                router.push('/dashboard');
            }
        }
    }, [user, isLoading, router]);

    // Fetch Users
    const { data: users, isLoading: usersLoading, refetch } = useQuery({
        queryKey: ['admin-users'],
        queryFn: async () => {
            const res = await api.get<any[]>('/admin/users');
            return res.data.map((u: any) => ({
                ...u,
                id: u.id || u._id || ''
            })) as UserData[];
        },
        enabled: !!user, // Only fetch if user is logged in
    });

    const handleDeleteUser = async () => {
        if (!deletingUser) return;
        try {
            await api.delete(`/admin/users/${deletingUser.id}`);
            toast.success('User deleted successfully');
            setDeletingUser(null);
            refetch();
        } catch (error: any) {
            toast.error(error.response?.data?.detail || 'Failed to delete user');
        }
    };

    // Fetch Managers (for Add Dialog)
    const { data: managers } = useQuery({
        queryKey: ['admin-managers'],
        queryFn: async () => {
            const res = await api.get<ManagerData[]>('/admin/managers');
            return res.data;
        },
        enabled: !!user
    });

    // Search State
    const [searchTerm, setSearchTerm] = useState('');

    // Transform managers for select
    const managerOptions = managers?.map(m => ({ id: m.employee_id, name: `${m.full_name} (${m.employee_id})` })) || [];

    // Filtered Users
    const filteredUsers = users?.filter(u =>
        u.full_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        u.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
        u.employee_id.toLowerCase().includes(searchTerm.toLowerCase())
    );

    if (isLoading || usersLoading) return <div className="p-8">Loading users...</div>;

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-3xl font-bold tracking-tight">Employee Directory</h1>
                <Button onClick={() => setIsAddOpen(true)}>
                    <Plus className="mr-2 h-4 w-4" /> Add User
                </Button>
            </div>

            {/* Search Input */}
            <div className="flex items-center space-x-2">
                <Input
                    placeholder="Search by name, email, or ID..."
                    value={searchTerm}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSearchTerm(e.target.value)}
                    className="max-w-sm"
                />
            </div>

            <Card>
                <CardContent className="p-0">
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>ID</TableHead>
                                <TableHead>Name</TableHead>
                                <TableHead>Role</TableHead>
                                <TableHead>Manager</TableHead>
                                <TableHead className="text-center">Casual/Earned Leave</TableHead>
                                <TableHead className="text-center">Sick Leave</TableHead>
                                <TableHead className="text-center">Comp Off</TableHead>
                                <TableHead className="text-right">Actions</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {filteredUsers?.map((u) => {
                                const managerName = u.manager_id
                                    ? (users?.find(m => m.employee_id === u.manager_id)?.full_name || u.manager_id)
                                    : '-';

                                return (
                                    <TableRow key={u.employee_id}>
                                        <TableCell className="font-medium">{u.employee_id}</TableCell>
                                        <TableCell>
                                            <div className="flex flex-col">
                                                <span>{u.full_name}</span>
                                                <span className="text-xs text-slate-500">{u.email}</span>
                                            </div>
                                        </TableCell>
                                        <TableCell className="capitalize">{u.role}</TableCell>
                                        <TableCell className="whitespace-nowrap">{managerName}</TableCell>
                                        <TableCell className="text-center">{u.casual_balance + u.earned_balance}</TableCell>
                                        <TableCell className="text-center">{u.sick_balance}</TableCell>
                                        <TableCell className="text-center">{u.comp_off_balance}</TableCell>
                                        <TableCell className="text-right">
                                            <DropdownMenu>
                                                <DropdownMenuTrigger asChild>
                                                    <Button variant="ghost" className="h-8 w-8 p-0">
                                                        <span className="sr-only">Open menu</span>
                                                        <MoreVertical className="h-4 w-4" />
                                                    </Button>
                                                </DropdownMenuTrigger>
                                                <DropdownMenuContent align="end">
                                                    <DropdownMenuLabel>Actions</DropdownMenuLabel>
                                                    <DropdownMenuItem onClick={() => setEditingDetailsUser(u)}>
                                                        <UserCog className="mr-2 h-4 w-4" />
                                                        Edit Details
                                                    </DropdownMenuItem>
                                                    <DropdownMenuItem onClick={() => setEditingBalanceUser(u)}>
                                                        <CreditCard className="mr-2 h-4 w-4" />
                                                        Edit Balance
                                                    </DropdownMenuItem>
                                                    <DropdownMenuSeparator />
                                                    <DropdownMenuItem
                                                        onClick={() => setDeletingUser(u)}
                                                        className="text-red-600 focus:text-red-600"
                                                    >
                                                        <Trash className="mr-2 h-4 w-4" />
                                                        Delete User
                                                    </DropdownMenuItem>
                                                </DropdownMenuContent>
                                            </DropdownMenu>
                                        </TableCell>
                                    </TableRow>
                                );
                            })}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>

            <AddUserDialog
                isOpen={isAddOpen}
                onClose={() => setIsAddOpen(false)}
                managers={managerOptions}
            />

            <EditBalanceDialog
                isOpen={!!editingBalanceUser}
                onClose={() => setEditingBalanceUser(null)}
                user={editingBalanceUser}
            />

            <EditUserDialog
                isOpen={!!editingDetailsUser}
                onClose={() => setEditingDetailsUser(null)}
                user={editingDetailsUser}
                onSuccess={refetch}
            />

            <AlertDialog open={!!deletingUser} onOpenChange={() => setDeletingUser(null)}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Are you sure?</AlertDialogTitle>
                        <AlertDialogDescription>
                            This action cannot be undone. This will permanently delete the user
                            <span className="font-semibold text-slate-900 mx-1">{deletingUser?.full_name}</span>
                            and remove their data from our servers.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction onClick={handleDeleteUser} className="bg-red-600 hover:bg-red-700">
                            Delete
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
}
