'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { toast } from 'sonner';
import { Loader2, CalendarIcon } from 'lucide-react';
import { format } from 'date-fns';
import { useQueryClient } from '@tanstack/react-query';

import api from '@/lib/axios';
import { Button } from '@/components/ui/button';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Calendar } from '@/components/ui/calendar';
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from '@/components/ui/popover';
import { cn } from '@/lib/utils';

// Schema
const addUserSchema = z.object({
    full_name: z.string().min(2, 'Name is required'),
    email: z.string().email('Invalid email'),
    employee_id: z.string().min(1, 'Employee ID is required'),
    role: z.string().transform((val) => val?.toLowerCase() || 'employee'), // Transform to lowercase
    manager_employee_id: z.string().optional(), // Backend expects manager_employee_id, not manager_id
    joining_date: z.date(),
    password: z.string().min(6, 'Password must be at least 6 characters'),
    employee_type: z.string().optional(),
});

// Assuming POST /admin/users endpoint structure from previous context
// create_user_admin(user: UserCreateAdmin)
// UserCreateAdmin likely needs: email, password, full_name, role, employee_id, joining_date, manager_id.

type UserFormValues = z.infer<typeof addUserSchema>;

interface AddUserDialogProps {
    isOpen: boolean;
    onClose: () => void;
    managers: { id: string; name: string }[];
}

export function AddUserDialog({ isOpen, onClose, managers }: AddUserDialogProps) {
    const queryClient = useQueryClient();
    const [loading, setLoading] = useState(false);

    const {
        register,
        handleSubmit,
        setValue,
        watch,
        reset,
        formState: { errors },
    } = useForm<UserFormValues>({
        resolver: zodResolver(addUserSchema),
        defaultValues: {
            role: 'employee',
            employee_type: 'Full-time',
        },
    });

    const selectedDate = watch('joining_date');
    const selectedRole = watch('role');

    const onSubmit = async (data: UserFormValues) => {
        setLoading(true);
        try {
            // Force role to lowercase - handle any case variations
            const roleValue = String(data.role || selectedRole || 'employee').toLowerCase().trim();
            
            // Validate role is one of the allowed values
            const allowedRoles = ['employee', 'manager', 'hr', 'admin', 'founder', 'intern', 'contract'];
            if (!allowedRoles.includes(roleValue)) {
                toast.error(`Invalid role: ${roleValue}. Please select a valid role.`);
                setLoading(false);
                return;
            }
            
            // Prepare payload matching backend UserCreateAdmin model
            const payload: any = {
                full_name: data.full_name,
                email: data.email,
                employee_id: data.employee_id,
                password: data.password,
                role: roleValue, // Explicitly lowercase
                joining_date: format(data.joining_date, 'yyyy-MM-dd'),
                employee_type: data.employee_type || 'Full-time',
            };
            
            // Only include manager_employee_id if a manager is selected
            if (data.manager_employee_id && data.manager_employee_id !== 'none') {
                payload.manager_employee_id = data.manager_employee_id;
            }
            
            await api.post('/admin/users', payload);

            toast.success('User created successfully');
            queryClient.invalidateQueries({ queryKey: ['admin-users'] });
            reset();
            onClose();
        } catch (error: any) {
            toast.error(error.response?.data?.detail || 'Failed to create user');
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="sm:max-w-[500px]">
                <DialogHeader>
                    <DialogTitle>Add New User</DialogTitle>
                    <DialogDescription>
                        Create a new employee record in the system.
                    </DialogDescription>
                </DialogHeader>

                <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label>Full Name</Label>
                            <Input {...register('full_name')} placeholder="John Doe" />
                            {errors.full_name && <p className="text-red-500 text-xs">{errors.full_name.message}</p>}
                        </div>
                        <div className="space-y-2">
                            <Label>Employee ID</Label>
                            <Input {...register('employee_id')} placeholder="EMP001" />
                            {errors.employee_id && <p className="text-red-500 text-xs">{errors.employee_id.message}</p>}
                        </div>
                    </div>

                    <div className="space-y-2">
                        <Label>Email</Label>
                        <Input {...register('email')} type="email" placeholder="john@example.com" />
                        {errors.email && <p className="text-red-500 text-xs">{errors.email.message}</p>}
                    </div>

                    <div className="space-y-2">
                        <Label>Password</Label>
                        <Input {...register('password')} type="password" placeholder="Initial password" />
                        {errors.password && <p className="text-red-500 text-xs">{errors.password.message}</p>}
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label>Role</Label>
                            <Select 
                                value={selectedRole || 'employee'} 
                                onValueChange={(val) => {
                                    const lowerVal = val.toLowerCase();
                                    setValue('role', lowerVal, { shouldValidate: true });
                                }}
                            >
                                <SelectTrigger>
                                    <SelectValue placeholder="Select role" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="employee">Employee</SelectItem>
                                    <SelectItem value="manager">Manager</SelectItem>
                                    <SelectItem value="hr">HR</SelectItem>
                                    <SelectItem value="founder">Founder</SelectItem>
                                    <SelectItem value="admin">Admin</SelectItem>
                                    <SelectItem value="intern">Intern</SelectItem>
                                    <SelectItem value="contract">Contract</SelectItem>
                                </SelectContent>
                            </Select>
                            {errors.role && <p className="text-red-500 text-xs">{errors.role.message}</p>}
                        </div>

                        <div className="space-y-2">
                            <Label>Manager (Optional)</Label>
                            <Select onValueChange={(val) => setValue('manager_employee_id', val === "none" ? undefined : val)}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Select manager" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="none">None</SelectItem>
                                    {managers.map((m) => (
                                        <SelectItem key={m.id} value={m.id}>
                                            {m.name}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    <div className="space-y-2 flex flex-col">
                        <Label>Joining Date</Label>
                        <Popover>
                            <PopoverTrigger asChild>
                                <Button
                                    variant={"outline"}
                                    className={cn(
                                        "w-full pl-3 text-left font-normal",
                                        !selectedDate && "text-muted-foreground"
                                    )}
                                >
                                    {selectedDate ? (
                                        format(selectedDate, "PPP")
                                    ) : (
                                        <span>Pick a date</span>
                                    )}
                                    <CalendarIcon className="ml-auto h-4 w-4 opacity-50" />
                                </Button>
                            </PopoverTrigger>
                            <PopoverContent className="w-auto p-0" align="start">
                                <Calendar
                                    mode="single"
                                    selected={selectedDate}
                                    onSelect={(date) => date && setValue('joining_date', date)}
                                    disabled={(date) =>
                                        date > new Date() || date < new Date("1900-01-01")
                                    }
                                    initialFocus
                                />
                            </PopoverContent>
                        </Popover>
                        {errors.joining_date && <p className="text-red-500 text-xs">{errors.joining_date.message}</p>}
                    </div>

                    <Button type="submit" className="w-full" disabled={loading}>
                        {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Create User
                    </Button>
                </form>
            </DialogContent>
        </Dialog>
    );
}
