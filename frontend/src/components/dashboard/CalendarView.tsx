'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
    format,
    startOfMonth,
    endOfMonth,
    startOfWeek,
    endOfWeek,
    eachDayOfInterval,
    isSameMonth,
    isSameDay,
    addMonths,
    subMonths,
    isToday,
    parseISO,
    isWeekend
} from 'date-fns';
import { ChevronLeft, ChevronRight, Loader2 } from 'lucide-react';

import api from '@/lib/axios';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { DateRange } from 'react-day-picker';

// Types
interface Holiday {
    date: string;
    name: string;
    is_optional?: boolean;
}

interface Leave {
    id: string;
    start_date: string; // YYYY-MM-DD
    end_date: string;   // YYYY-MM-DD
    type: string;
    status: 'APPROVED' | 'PENDING' | 'REJECTED' | 'CANCELLED' | 'CANCELLATION_REQUESTED';
}

interface CalendarViewProps {
    onDateSelect: (range: DateRange) => void;
}

export function CalendarView({ onDateSelect }: CalendarViewProps) {
    const [currentMonth, setCurrentMonth] = useState(new Date());

    // 1. Fetch Data
    const { data: holidays, isLoading: holidaysLoading } = useQuery({
        queryKey: ['calendar-holidays'],
        queryFn: async () => {
            const res = await api.get<Holiday[]>('/calendar/holidays');
            return res.data;
        }
    });

    const { data: leaves, isLoading: leavesLoading } = useQuery({
        queryKey: ['my-leaves'],
        queryFn: async () => {
            const res = await api.get<Leave[]>('/leaves/mine');
            return res.data;
        }
    });

    const isLoading = holidaysLoading || leavesLoading;

    // 2. Navigation Actions
    const nextMonth = () => setCurrentMonth(addMonths(currentMonth, 1));
    const prevMonth = () => setCurrentMonth(subMonths(currentMonth, 1));

    // 3. Generate Grid
    const monthStart = startOfMonth(currentMonth);
    const monthEnd = endOfMonth(monthStart);
    const startDate = startOfWeek(monthStart);
    const endDate = endOfWeek(monthEnd);

    const calendarDays = eachDayOfInterval({
        start: startDate,
        end: endDate,
    });

    const weekDays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

    // 4. Helper to get data for a day
    const getDayData = (date: Date) => {
        const dateStr = format(date, 'yyyy-MM-dd');

        // Check Holiday
        const holiday = holidays?.find(h => h.date === dateStr);

        // Check Leave
        // Need to check if date falls within [start, end] range of any leave
        const leave = leaves?.find(l => {
            const start = l.start_date;
            const end = l.end_date; // Can be null for Sabbatical

            const isActive = l.status !== 'REJECTED' &&
                l.status !== 'CANCELLED' &&
                l.status !== 'CANCELLATION_REQUESTED';

            if (!isActive) return false;

            if (!end) {
                // Open-ended (Sabbatical)
                return dateStr >= start;
            }

            return dateStr >= start && dateStr <= end;
        });

        return { holiday, leave };
    };

    // 5. Interaction
    // Drag Selection State
    const [dragStart, setDragStart] = useState<Date | null>(null);
    const [currentDragDate, setCurrentDragDate] = useState<Date | null>(null);
    const [isDragging, setIsDragging] = useState(false);

    const handleMouseDown = (date: Date) => {
        setIsDragging(true);
        setDragStart(date);
        setCurrentDragDate(date);
    };

    const handleMouseEnter = (date: Date) => {
        if (isDragging) {
            setCurrentDragDate(date);
        }
    };

    const handleMouseUp = () => {
        if (isDragging && dragStart && currentDragDate) {
            const start = dragStart < currentDragDate ? dragStart : currentDragDate;
            const end = dragStart < currentDragDate ? currentDragDate : dragStart;

            onDateSelect({ from: start, to: end });
        }
        // Reset drag state
        setIsDragging(false);
        setDragStart(null);
        setCurrentDragDate(null);
    };

    // Helper to check if a day is within the current drag selection
    const isDaySelected = (date: Date) => {
        if (!isDragging || !dragStart || !currentDragDate) return false;
        const start = dragStart < currentDragDate ? dragStart : currentDragDate;
        const end = dragStart < currentDragDate ? currentDragDate : dragStart;
        return date >= start && date <= end;
    };

    if (isLoading) {
        return (
            <Card className="h-full min-h-[400px] flex items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
            </Card>
        );
    }

    return (
        <Card className="h-full flex flex-col" onMouseUp={handleMouseUp} onMouseLeave={handleMouseUp}>
            <CardHeader className="flex flex-row items-center justify-between py-4">
                <CardTitle className="text-lg font-semibold">
                    {format(currentMonth, 'MMMM yyyy')}
                </CardTitle>
                <div className="flex space-x-2">
                    <Button variant="outline" size="icon" onClick={prevMonth}>
                        <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <Button variant="outline" size="icon" onClick={nextMonth}>
                        <ChevronRight className="h-4 w-4" />
                    </Button>
                </div>
            </CardHeader>
            <CardContent className="flex-1 p-0 select-none">
                {/* Header Row */}
                <div className="grid grid-cols-7 border-b bg-slate-50 dark:bg-slate-900">
                    {weekDays.map((day) => (
                        <div key={day} className="py-2 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider">
                            {day}
                        </div>
                    ))}
                </div>

                {/* Days Grid */}
                <div className="grid grid-cols-7 auto-rows-fr h-full min-h-[300px]">
                    {calendarDays.map((day, idx) => {
                        const { holiday, leave } = getDayData(day);
                        const isCurrentMonth = isSameMonth(day, monthStart);
                        const isTodayDate = isToday(day);
                        const isSelected = isDaySelected(day);

                        // Logic to show/hide leave on weekends
                        // Standard: Hide on weekends
                        // Maternity/Sabbatical: Show on weekends
                        const showLeave = leave && (
                            !isWeekend(day) ||
                            ['MATERNITY', 'SABBATICAL'].includes(leave.type)
                        ) && !holiday;

                        return (
                            <div
                                key={day.toString()}
                                onMouseDown={() => handleMouseDown(day)}
                                onMouseEnter={() => handleMouseEnter(day)}
                                className={cn(
                                    "min-h-[80px] p-2 border-b border-r relative transition-colors cursor-pointer flex flex-col gap-1",
                                    // Base colors
                                    !isCurrentMonth && "bg-slate-50 text-slate-400 dark:bg-slate-900/50",
                                    isCurrentMonth && "hover:bg-slate-50/50",

                                    // Selection State
                                    isSelected && "bg-indigo-50 ring-2 ring-indigo-500 z-20",

                                    // Today State (lower priority than selection)
                                    isTodayDate && !isSelected && "ring-2 ring-indigo-500 ring-inset z-10",

                                    // Holiday Styling (background)
                                    holiday && !isSelected && "bg-purple-50 hover:bg-purple-100",
                                )}
                            >
                                <span className={cn(
                                    "text-xs font-medium w-6 h-6 flex items-center justify-center rounded-full",
                                    isTodayDate && "bg-indigo-600 text-white",
                                    !isTodayDate && "text-slate-700"
                                )}>
                                    {format(day, 'd')}
                                </span>

                                {/* Holiday Badge */}
                                {holiday && (
                                    <div className="mt-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-purple-100 text-purple-700 truncate border border-purple-200" title={holiday.name}>
                                        {holiday.name}
                                    </div>
                                )}

                                {/* Leave Badge */}
                                {showLeave && (
                                    <div
                                        className={cn(
                                            "mt-auto px-1.5 py-0.5 rounded text-[10px] font-medium border truncate",
                                            leave!.status === 'APPROVED' && "bg-emerald-100 text-emerald-800 border-emerald-200",
                                            leave!.status === 'PENDING' && "bg-amber-100 text-amber-800 border-amber-200",
                                            leave!.status === 'REJECTED' && "bg-red-50 text-red-600 border-red-100 opacity-60"
                                        )}
                                        title={`${leave!.type} - ${leave!.status}`}
                                        onMouseDown={(e) => e.stopPropagation()}
                                    >
                                        {leave!.type.replace('_', ' ')}
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            </CardContent>
        </Card>
    );
}
