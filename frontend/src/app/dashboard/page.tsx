'use client';

import { useAuth } from '@/hooks/useAuth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { CalendarView } from '@/components/dashboard/CalendarView';
import { useQuery } from '@tanstack/react-query';
import { format, parseISO } from 'date-fns';
import api from '@/lib/axios';

import { useState } from 'react';
import { Plus, Clock, UserCircle, Laptop } from 'lucide-react';
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
      <div className="grid gap-6 md:grid-cols-4">
        {/* Casual Leave - Teal Gradient */}
        <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-teal-50 to-teal-100 dark:from-teal-900/20 dark:to-teal-900/10 shadow-sm transition-all hover:shadow-md">
          <div className="absolute top-0 right-0 p-4 opacity-10">
            <UserCircle className="h-24 w-24 text-teal-600" />
          </div>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-1 z-10">
            <CardTitle className="text-sm font-semibold text-teal-700 dark:text-teal-300">Casual Leave</CardTitle>
          </CardHeader>
          <CardContent className="z-10">
            <div className="text-4xl font-bold text-teal-900 dark:text-teal-100">{user.casual_balance}</div>
            <p className="text-xs font-medium text-teal-600/80 dark:text-teal-400 mt-1">Available days</p>
          </CardContent>
        </Card>

        {/* Sick Leave - Blue Gradient */}
        <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/20 dark:to-blue-900/10 shadow-sm transition-all hover:shadow-md">
          <div className="absolute top-0 right-0 p-4 opacity-10">
            <Plus className="h-24 w-24 text-blue-600" />
          </div>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-1 z-10">
            <CardTitle className="text-sm font-semibold text-blue-700 dark:text-blue-300">Sick Leave</CardTitle>
          </CardHeader>
          <CardContent className="z-10">
            <div className="text-4xl font-bold text-blue-900 dark:text-blue-100">{user.sick_balance}</div>
            <p className="text-xs font-medium text-blue-600/80 dark:text-blue-400 mt-1">Available days</p>
          </CardContent>
        </Card>

        {/* Work From Home - Orange Gradient */}
        <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-orange-50 to-orange-100 dark:from-orange-900/20 dark:to-orange-900/10 shadow-sm transition-all hover:shadow-md">
          <div className="absolute top-0 right-0 p-4 opacity-10">
            <Laptop className="h-24 w-24 text-orange-600" />
          </div>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-1 z-10">
            <CardTitle className="text-sm font-semibold text-orange-700 dark:text-orange-300">Work From Home</CardTitle>
          </CardHeader>
          <CardContent className="z-10">
            <div className="text-4xl font-bold text-orange-900 dark:text-orange-100">{user.wfh_balance}</div>
            <p className="text-xs font-medium text-orange-600/80 dark:text-orange-400 mt-1">Available days</p>
          </CardContent>
        </Card>

        {/* Comp-Off - Purple Gradient */}
        <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-900/20 dark:to-purple-900/10 shadow-sm transition-all hover:shadow-md">
          <div className="absolute top-0 right-0 p-4 opacity-10">
            <Clock className="h-24 w-24 text-purple-600" />
          </div>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-1 z-10">
            <CardTitle className="text-sm font-semibold text-purple-700 dark:text-purple-300">Comp-Off</CardTitle>
          </CardHeader>
          <CardContent className="z-10">
            <div className="text-4xl font-bold text-purple-900 dark:text-purple-100">{user.comp_off_balance}</div>
            <p className="text-xs font-medium text-purple-600/80 dark:text-purple-400 mt-1">Approved claims</p>
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
            <div key={h._id || h.id} className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3 last:border-0 last:pb-0">
              <div className="space-y-1">
                <p className="text-sm font-medium leading-none text-slate-900 dark:text-slate-100">{h.name}</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  {format(parseISO(h.date), 'EEE, MMM d')}
                </p>
              </div>
              {h.is_optional && (
                <span className="inline-flex items-center px-2 py-1 rounded-md text-[10px] font-medium bg-amber-50 text-amber-700 border border-amber-200">
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
