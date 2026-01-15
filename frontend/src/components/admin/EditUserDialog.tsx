'use client';

import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { useQuery } from '@tanstack/react-query';

import api from '@/lib/axios';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';

const schema = z.object({
    full_name: z.string().min(2, 'Name must be at least 2 characters'),
    email: z.string().email('Invalid email address'),
    employee_id: z.string().min(1, 'Employee ID is required'),
    role: z.string().min(1, 'Role is required'),
    manager_id: z.string().optional().nullable(), // Allow null
    joining_date: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

// Helper for manager fetching
const useManagers = () => {
    return useQuery({
        queryKey: ['managers'],
        queryFn: async () => {
            const res = await api.get('/admin/managers');
            return res.data; // [{ employee_id, full_name, role }]
        }
    });
};

interface EditUserDialogProps {
    user: any;
    isOpen: boolean;
    onClose: () => void;
    onSuccess: () => void;
}

export default function EditUserDialog({ user, isOpen, onClose, onSuccess }: EditUserDialogProps) {
    const [isLoading, setIsLoading] = useState(false);
    const { data: managers } = useManagers();

    const {
        register,
        handleSubmit,
        reset,
        setValue,
        formState: { errors }
    } = useForm<FormValues>({
        resolver: zodResolver(schema),
    });

    useEffect(() => {
        if (user && isOpen) {
            reset({
                full_name: user.full_name,
                email: user.email,
                employee_id: user.employee_id,
                role: user.role,
                manager_id: user.manager_id || 'none', // Handle null
                joining_date: user.joining_date || undefined
            });
        }
    }, [user, isOpen, reset]);

    const onSubmit = async (data: FormValues) => {
        if (!user) return;
        setIsLoading(true);
        try {
            const payload = { ...data };
            if (payload.manager_id === 'none') {
                payload.manager_id = null;
            }
            // Use the correct ID (id or _id)
            const userId = user.id || user._id;
            await api.patch(`/admin/users/${userId}`, payload);

            toast.success('User updated successfully');
            onSuccess();
            onClose();
        } catch (error: any) {
            const detail = error.response?.data?.detail;
            toast.error(typeof detail === 'string' ? detail : 'Failed to update user');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="sm:max-w-[500px]">
                <DialogHeader>
                    <DialogTitle>Edit User Details</DialogTitle>
                    <DialogDescription>
                        Update profile information for {user?.full_name}
                    </DialogDescription>
                </DialogHeader>

                <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 py-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label>Employee ID</Label>
                            <Input {...register('employee_id')} />
                            {errors.employee_id && <p className="text-red-500 text-xs">{errors.employee_id.message}</p>}
                        </div>
                        <div className="space-y-2">
                            <Label>Full Name</Label>
                            <Input {...register('full_name')} />
                            {errors.full_name && <p className="text-red-500 text-xs">{errors.full_name.message}</p>}
                        </div>
                    </div>

                    <div className="space-y-2">
                        <Label>Email Address</Label>
                        <Input {...register('email')} />
                        {errors.email && <p className="text-red-500 text-xs">{errors.email.message}</p>}
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label>Role</Label>
                            <Select
                                onValueChange={(val) => setValue('role', val)}
                                defaultValue={user?.role}
                            >
                                <SelectTrigger>
                                    <SelectValue placeholder="Select role" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="employee">Employee</SelectItem>
                                    <SelectItem value="manager">Manager</SelectItem>
                                    <SelectItem value="hr">HR</SelectItem>
                                    <SelectItem value="founder">Founder</SelectItem>
                                    <SelectItem value="contract">Contractor</SelectItem>
                                    <SelectItem value="intern">Intern</SelectItem>
                                    <SelectItem value="admin">Admin</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-2">
                            <Label>Joining Date</Label>
                            <Input type="date" {...register('joining_date')} />
                        </div>
                    </div>

                    <div className="space-y-2">
                        <Label>Reporting Manager</Label>
                        <Select
                            onValueChange={(val) => setValue('manager_id', val)}
                            defaultValue={user?.manager_id || 'none'}
                        >
                            <SelectTrigger>
                                <SelectValue placeholder="Select manager" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="none">None</SelectItem>
                                {managers?.map((m: any) => (
                                    <SelectItem key={m.employee_id} value={m.employee_id}>
                                        {m.full_name} ({m.role})
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    <DialogFooter>
                        <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
                        <Button type="submit" disabled={isLoading}>
                            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Save Changes
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
