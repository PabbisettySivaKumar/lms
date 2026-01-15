'use client';

import { useAuth } from '@/hooks/useAuth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { CalendarView } from '@/components/dashboard/CalendarView';
import { useQuery } from '@tanstack/react-query';
import { format, parseISO } from 'date-fns';
import api from '@/lib/axios';

import { useState } from 'react';
import { Plus, Clock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ClaimCompOffDialog } from '@/components/dashboard/ClaimCompOffDialog';

import { ApplyLeaveDialog } from '@/components/dashboard/ApplyLeaveDialog';
import { DateRange } from 'react-day-picker';

export default function DashboardPage() {
  const { user, isLoading } = useAuth();
  const [isCompOffOpen, setIsCompOffOpen] = useState(false);
  const [isApplyOpen, setIsApplyOpen] = useState(false);
  const [selectedDate, setSelectedDate] = useState<DateRange | undefined>(undefined);

  if (isLoading || !user) {
    return (
      <div className="space-y-6">
        <h1 className="h-8 w-48 bg-slate-200 animate-pulse rounded" />
        <div className="grid gap-4 md:grid-cols-3">
          <div className="h-32 rounded-xl bg-slate-200 animate-pulse" />
          <div className="h-32 rounded-xl bg-slate-200 animate-pulse" />
          <div className="h-32 rounded-xl bg-slate-200 animate-pulse" />
        </div>
        <div className="h-96 rounded-xl bg-slate-200 animate-pulse" />
      </div>
    );
  }

  const handleApplyClick = () => {
    setSelectedDate(undefined); // Reset for clean state or could set to today
    setIsApplyOpen(true);
  };

  const handleCalendarSelect = (range: DateRange) => {
    setSelectedDate(range);
    setIsApplyOpen(true);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">Dashboard</h1>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setIsCompOffOpen(true)}>
            <Clock className="mr-2 h-4 w-4" />
            Claim Comp Off
          </Button>
          <Button onClick={handleApplyClick}>
            <Plus className="mr-2 h-4 w-4" />
            Apply for Leave
          </Button>
        </div>
      </div>

      <ClaimCompOffDialog
        isOpen={isCompOffOpen}
        onClose={() => setIsCompOffOpen(false)}
      />

      <ApplyLeaveDialog
        isOpen={isApplyOpen}
        onClose={() => setIsApplyOpen(false)}
        selectedDate={selectedDate}
      />

      {/* Section 1: Balances */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Casual Leave</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{user.casual_balance}</div>
            <p className="text-xs text-slate-500">Available days</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Sick Leave</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{user.sick_balance}</div>
            <p className="text-xs text-slate-500">Available days</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Comp-Off</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{user.comp_off_balance}</div>
            <p className="text-xs text-slate-500">Approved claims</p>
          </CardContent>
        </Card>
      </div>

      {/* Section 2: Main Content Area */}
      <div className="grid gap-4 md:grid-cols-7">
        {/* Calendar - Spans 5 cols */}
        <div className="md:col-span-5">
          <CalendarView onDateSelect={handleCalendarSelect} />
        </div>

        {/* Holidays Widget - Spans 2 cols */}
        <div className="md:col-span-2">
          <HolidayWidget />
        </div>
      </div>
    </div>
  );
}

function HolidayWidget() {
  const { data: holidays } = useQuery({
    queryKey: ['calendar-holidays'],
    queryFn: async () => {
      const res = await api.get<any[]>('/calendar/holidays');
      return res.data;
    }
  });

  const currentYear = new Date().getFullYear();
  const filteredHolidays = holidays?.filter(h =>
    new Date(h.date).getFullYear() === currentYear
  ) || [];

  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <CardTitle>Holidays {currentYear}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4 max-h-[400px] overflow-y-auto pr-2">
          {filteredHolidays.length === 0 && (
            <p className="text-sm text-slate-500">No holidays found for this year.</p>
          )}
          {filteredHolidays.map((h: any) => (
            <div key={h._id || h.id} className="flex items-center justify-between border-b pb-2 last:border-0 last:pb-0">
              <div className="space-y-1">
                <p className="text-sm font-medium leading-none">{h.name}</p>
                <p className="text-xs text-slate-500">
                  {format(parseISO(h.date), 'EEE, MMM d')}
                </p>
              </div>
              {h.is_optional && (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-blue-50 text-blue-700 border border-blue-200">
                  Optional
                </span>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
