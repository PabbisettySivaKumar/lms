'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { format } from 'date-fns';
import { toast } from 'sonner';
import { DateRange } from 'react-day-picker';
import { Loader2, CalendarIcon } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';
import { cn } from '@/lib/utils';
import { Calendar } from '@/components/ui/calendar';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { useEffect } from 'react';

import api from '@/lib/axios';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';

const applySchema = z.object({
  type: z.enum(['CASUAL', 'SICK', 'EARNED', 'COMP_OFF', 'MATERNITY', 'SABBATICAL', 'WFH']),
  reason: z.string().min(1, 'Reason is required'),
});

type ApplyValues = z.infer<typeof applySchema>;

interface ApplyLeaveDialogProps {
  isOpen: boolean;
  onClose: () => void;
  selectedDate: DateRange | undefined;
}

export function ApplyLeaveDialog({
  isOpen,
  onClose,
  selectedDate,
}: ApplyLeaveDialogProps) {
  const queryClient = useQueryClient();
  const [loading, setLoading] = useState(false);

  // Local date state to allow changing it
  const [date, setDate] = useState<DateRange | undefined>(selectedDate);

  // Sync prop changes to local state when dialog opens
  useEffect(() => {
    if (isOpen) {
      setDate(selectedDate);
    }
  }, [isOpen, selectedDate]);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors }
  } = useForm<ApplyValues>({
    resolver: zodResolver(applySchema),
    defaultValues: {
      type: 'CASUAL',
      reason: ''
    }
  });

  const selectedType = watch('type');

  // Logic for Maternity/Sabbatical display
  const isMaternity = selectedType === 'MATERNITY';
  const isSabbatical = selectedType === 'SABBATICAL';

  const onSubmit = async (data: ApplyValues) => {
    if (!date?.from) {
      toast.error('Please select a start date');
      return;
    }

    // Validation for Standard/Maternity types requiring End Date
    if (!isSabbatical && !date.to && !isMaternity) {
      // Note: Maternity end date is auto-calced or assumed by backend if we send single range?
      // Actually for Maternity, we might want to visually show the range.
      // But if user clicks ONE date, 'to' might be undefined.
      // Let's handle formatting below.
      toast.error('Please select an end date');
      return;
    }

    setLoading(true);
    try {
      let endDateStr = date.to ? format(date.to, 'yyyy-MM-dd') : format(date.from, 'yyyy-MM-dd');

      // Override for Maternity/Sabbatical logic
      if (isSabbatical) {
        endDateStr = null as any; // Backend handles null
      } else if (isMaternity) {
        // Send the start date, backend Auto-Calcs? Or we send calculated?
        // Backend has logic: "calculated_end = leave.start_date + timedelta(days=179)"
        // So we can send anything or nothing for end_date, backend overrides.
        // Let's just send the start date as end date to satisfy payload schema if needed, or null.
        // Schema says end_date is Optional now. So null is fine.
        endDateStr = null as any;
      }

      await api.post('/leaves/apply', {
        type: data.type,
        start_date: format(date.from, 'yyyy-MM-dd'),
        end_date: endDateStr,
        reason: data.reason
      });

      toast.success('Leave applied successfully');
      queryClient.invalidateQueries({ queryKey: ['user-balances'] });
      queryClient.invalidateQueries({ queryKey: ['my-leaves'] });
      reset();
      onClose();
    } catch (error: any) {
      const detail = error.response?.data?.detail;
      let errorMessage = 'Failed to apply';

      if (typeof detail === 'string') {
        errorMessage = detail;
      } else if (Array.isArray(detail)) {
        // Pydantic validation error
        errorMessage = detail.map((err: any) => err.msg).join(', ');
      } else if (typeof detail === 'object') {
        errorMessage = JSON.stringify(detail);
      }

      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  // Helper text for end date
  let endDateInfo = "";
  if (isMaternity && date?.from) {
    const mEnd = new Date(date.from);
    mEnd.setDate(mEnd.getDate() + 179);
    endDateInfo = `Ends: ${format(mEnd, 'MMM d, yyyy')} (180 days)`;
  } else if (isSabbatical) {
    endDateInfo = "Indefinite Duration";
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Apply for Leave</DialogTitle>
          <DialogDescription>
            Select dates and leave type
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">

          {/* Date Picker Section */}
          <div className="space-y-2">
            <Label>Dates</Label>
            <div className={cn("grid gap-2", { "grid-cols-1": true })}>
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    id="date"
                    variant={"outline"}
                    className={cn(
                      "w-full justify-start text-left font-normal",
                      !date && "text-muted-foreground"
                    )}
                  >
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {date?.from ? (
                      date.to ? (
                        <>
                          {format(date.from, "LLL dd, y")} -{" "}
                          {format(date.to, "LLL dd, y")}
                        </>
                      ) : (
                        format(date.from, "LLL dd, y")
                      )
                    ) : (
                      <span>Pick a date range</span>
                    )}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="start">
                  <Calendar
                    initialFocus
                    mode="range"
                    defaultMonth={date?.from}
                    selected={date}
                    onSelect={setDate}
                    numberOfMonths={2}
                    disabled={(date) => date < new Date('1900-01-01')} // Optional constraint
                  />
                </PopoverContent>
              </Popover>
            </div>
            {/* Automatic End Date Info */}
            {(isMaternity || isSabbatical) && (
              <p className="text-xs text-blue-600 font-medium">
                * {endDateInfo}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label>Leave Type</Label>
            <Select
              onValueChange={(val) => setValue('type', val as any)}
              defaultValue="CASUAL"
            >
              <SelectTrigger>
                <SelectValue placeholder="Select type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="CASUAL">Casual Leave</SelectItem>
                <SelectItem value="SICK">Sick Leave</SelectItem>
                <SelectItem value="EARNED">Earned Leave</SelectItem>
                <SelectItem value="WFH">Work From Home</SelectItem>
                <SelectItem value="COMP_OFF">Comp-Off</SelectItem>
                <SelectItem value="MATERNITY">Maternity Leave</SelectItem>
                <SelectItem value="SABBATICAL">Sabbatical Leave</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>Reason</Label>
            <Input {...register('reason')} placeholder="e.g., Personal work, Health issue" />
            {errors.reason && <p className="text-red-500 text-sm">{errors.reason.message}</p>}
          </div>

          <Button type="submit" className="w-full" disabled={loading || !date?.from}>
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Submit Request
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
