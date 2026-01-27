'use client';

import { useState, useEffect } from 'react'; // Added useEffect import
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { toast } from 'sonner';
import { Loader2 } from 'lucide-react';
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
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

const balanceSchema = z.object({
    casual_balance: z.number().min(0),
    sick_balance: z.number().min(0),
    earned_balance: z.number().min(0),
    comp_off_balance: z.number().min(0),
});

type BalanceValues = z.infer<typeof balanceSchema>;

interface EditBalanceDialogProps {
    isOpen: boolean;
    onClose: () => void;
    user: {
        id: number | string; // Backend returns integer, support both
        _id?: string; // Backward compatibility
        full_name: string;
        casual_balance?: number; // Optional, defaults to 0
        sick_balance?: number; // Optional, defaults to 0
        earned_balance?: number; // Optional, defaults to 0
        comp_off_balance?: number; // Optional, defaults to 0
    } | null;
}

export function EditBalanceDialog({ isOpen, onClose, user }: EditBalanceDialogProps) {
    const queryClient = useQueryClient();
    const [loading, setLoading] = useState(false);

    const {
        register,
        handleSubmit,
        reset,
        formState: { errors },
    } = useForm<BalanceValues>({
        resolver: zodResolver(balanceSchema),
    });

    // Reset form when user changes
    useEffect(() => {
        if (user) {
            reset({
                casual_balance: user.casual_balance || 0,
                sick_balance: user.sick_balance || 0,
                earned_balance: user.earned_balance || 0,
                comp_off_balance: user.comp_off_balance || 0,
            });
        }
    }, [user, reset]);


    const onSubmit = async (data: BalanceValues) => {
        if (!user) return;
        setLoading(true);
        try {
            // Backend accepts string IDs in URL and converts to integer
            await api.patch(`/admin/users/${String(user.id)}/balance`, data);

            toast.success('Balances updated successfully');
            queryClient.invalidateQueries({ queryKey: ['admin-users'] });
            onClose();
        } catch (error: any) {
            toast.error(error.response?.data?.detail || 'Failed to update balances');
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                    <DialogTitle>Edit Balances</DialogTitle>
                    <DialogDescription>
                        Update leave balances for {user?.full_name}
                    </DialogDescription>
                </DialogHeader>

                <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label>Casual Leave</Label>
                            <Input 
                                type="number" 
                                step="0.5" 
                                {...register('casual_balance', { valueAsNumber: true })} 
                            />
                            {errors.casual_balance && (
                                <p className="text-sm text-red-500">{errors.casual_balance.message}</p>
                            )}
                        </div>
                        <div className="space-y-2">
                            <Label>Sick Leave</Label>
                            <Input 
                                type="number" 
                                step="0.5" 
                                {...register('sick_balance', { valueAsNumber: true })} 
                            />
                            {errors.sick_balance && (
                                <p className="text-sm text-red-500">{errors.sick_balance.message}</p>
                            )}
                        </div>
                        <div className="space-y-2">
                            <Label>Earned Leave</Label>
                            <Input 
                                type="number" 
                                step="0.5" 
                                {...register('earned_balance', { valueAsNumber: true })} 
                            />
                            {errors.earned_balance && (
                                <p className="text-sm text-red-500">{errors.earned_balance.message}</p>
                            )}
                        </div>
                        <div className="space-y-2">
                            <Label>Comp-Off</Label>
                            <Input 
                                type="number" 
                                step="0.5" 
                                {...register('comp_off_balance', { valueAsNumber: true })} 
                            />
                            {errors.comp_off_balance && (
                                <p className="text-sm text-red-500">{errors.comp_off_balance.message}</p>
                            )}
                        </div>
                    </div>

                    <Button type="submit" className="w-full" disabled={loading}>
                        {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Update Balances
                    </Button>
                </form>
            </DialogContent>
        </Dialog>
    );
}
