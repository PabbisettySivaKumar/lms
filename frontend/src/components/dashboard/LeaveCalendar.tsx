'use client';

import { useState } from 'react';
import { DateRange } from 'react-day-picker';
import { useQuery } from '@tanstack/react-query';
import { format, isWeekend } from 'date-fns';

import api from '@/lib/axios';
import { Calendar } from '@/components/ui/calendar';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ApplyLeaveDialog } from './ApplyLeaveDialog';

interface Holiday {
    date: string;
    name: string;
    year: number;
}

export function LeaveCalendar() {
    const [date, setDate] = useState<DateRange | undefined>();
    const [isDialogOpen, setIsDialogOpen] = useState(false);

    // Fetch Holidays
    const { data: holidays } = useQuery({
        queryKey: ['holidays'],
        queryFn: async () => {
            const res = await api.get<Holiday[]>('/calendar/holidays'); // Ensure backend endpoint exists
            return res.data;
        }
    });

    // Fetch User Leaves
    const { data: myLeaves } = useQuery({
        queryKey: ['my-leaves'],
        queryFn: async () => {
            const res = await api.get<any[]>('/leaves/mine');
            return res.data;
        }
    });

    // Create Matchers
    const holidayDates = holidays?.map(h => new Date(h.date)) || [];

    const approvedDates: Date[] = [];
    const pendingDates: Date[] = [];

    myLeaves?.forEach(leave => {
        let current = new Date(leave.start_date);
        const end = new Date(leave.end_date);

        while (current <= end) {
            if (leave.status === 'APPROVED') {
                approvedDates.push(new Date(current));
            } else if (leave.status === 'PENDING') {
                pendingDates.push(new Date(current));
            }
            current.setDate(current.getDate() + 1);
        }
    });

    return (
        <Card className="col-span-1 h-full">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle>Calendar</CardTitle>
                <div className="flex gap-2">
                    <div className="flex items-center text-xs text-green-600 font-medium">
                        <div className="w-2 h-2 rounded-full bg-green-500 mr-1" /> Approved
                    </div>
                    <div className="flex items-center text-xs text-blue-600 font-medium">
                        <div className="w-2 h-2 rounded-full bg-blue-500 mr-1" /> Pending
                    </div>
                </div>
                <Button
                    size="sm"
                    onClick={() => setIsDialogOpen(true)}
                    disabled={!date?.from}
                >
                    Apply
                </Button>
            </CardHeader>
            <CardContent className="flex flex-col items-center">
                <Calendar
                    mode="range"
                    selected={date}
                    onSelect={setDate}
                    className="rounded-md border shadow-sm"
                    modifiers={{
                        holiday: holidayDates,
                        approved: approvedDates,
                        pending: pendingDates,
                        weekend: (date) => isWeekend(date)
                    }}
                    modifiersStyles={{
                        holiday: { color: 'red', fontWeight: 'bold' },
                        approved: { color: 'green', fontWeight: 'bold', backgroundColor: '#ecfdf5' },
                        pending: { color: 'blue', fontWeight: 'bold', backgroundColor: '#eff6ff' },
                        weekend: { color: 'gray' }
                    }}
                />
                <div className="mt-4 text-sm text-slate-500">
                    {date?.from ? (
                        <p>
                            Selected: {format(date.from, 'MMM dd')}
                            {date.to && ` - ${format(date.to, 'MMM dd')}`}
                        </p>
                    ) : (
                        <p>Select dates to apply</p>
                    )}
                </div>

                <ApplyLeaveDialog
                    isOpen={isDialogOpen}
                    onClose={() => setIsDialogOpen(false)}
                    selectedDate={date}
                />
            </CardContent>
        </Card>
    );
}
