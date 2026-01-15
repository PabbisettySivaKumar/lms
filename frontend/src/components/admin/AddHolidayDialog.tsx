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
const holidaySchema = z.object({
    name: z.string().min(2, 'Name is required'),
    date: z.date(),
    is_optional: z.boolean(),
});

type HolidayFormValues = z.infer<typeof holidaySchema>;

interface AddHolidayDialogProps {
    isOpen: boolean;
    onClose: () => void;
}

export function AddHolidayDialog({ isOpen, onClose }: AddHolidayDialogProps) {
    const queryClient = useQueryClient();
    const [loading, setLoading] = useState(false);

    // useForm
    const {
        register,
        handleSubmit,
        setValue,
        watch,
        reset,
        formState: { errors },
    } = useForm<HolidayFormValues>({
        resolver: zodResolver(holidaySchema),
        defaultValues: {
            name: '',
            is_optional: false,
        },
    });

    const selectedDate = watch('date');
    const isOptional = watch('is_optional');

    const onSubmit = async (data: HolidayFormValues) => {
        setLoading(true);
        try {
            await api.post('/admin/holidays', {
                ...data,
                date: format(data.date, 'yyyy-MM-dd'),
                year: data.date.getFullYear(),
            });

            toast.success('Holiday added successfully');
            queryClient.invalidateQueries({ queryKey: ['holidays'] });
            queryClient.invalidateQueries({ queryKey: ['calendar-holidays'] });
            reset();
            onClose();
        } catch (error: any) {
            const detail = error.response?.data?.detail;
            let errorMessage = 'Failed to add holiday';

            if (typeof detail === 'string') {
                errorMessage = detail;
            } else if (Array.isArray(detail)) {
                errorMessage = detail.map((err: any) => err.msg).join(', ');
            } else if (typeof detail === 'object' && detail !== null) {
                errorMessage = JSON.stringify(detail);
            }

            toast.error(errorMessage);
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                    <DialogTitle>Add Holiday</DialogTitle>
                    <DialogDescription>
                        Add a new public or optional holiday to the calendar.
                    </DialogDescription>
                </DialogHeader>

                <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                    <div className="space-y-2">
                        <Label>Holiday Name</Label>
                        <Input {...register('name')} placeholder="e.g. Independence Day" />
                        {errors.name && <p className="text-red-500 text-xs">{errors.name.message}</p>}
                    </div>

                    <div className="space-y-2 flex flex-col">
                        <Label>Date</Label>
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
                                    onSelect={(date) => date && setValue('date', date)}
                                    initialFocus
                                />
                            </PopoverContent>
                        </Popover>
                        {errors.date && <p className="text-red-500 text-xs">Date is required</p>}
                    </div>

                    <div className="flex items-center space-x-2">
                        <input
                            type="checkbox"
                            id="optional"
                            className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-600"
                            checked={isOptional}
                            onChange={(e) => setValue('is_optional', e.target.checked)}
                        />
                        <Label htmlFor="optional" className="text-sm font-medium leading-none cursor-pointer">
                            Is Optional Holiday?
                        </Label>
                    </div>

                    <Button type="submit" className="w-full" disabled={loading}>
                        {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Add Holiday
                    </Button>
                </form>
            </DialogContent>
        </Dialog>
    );
}
