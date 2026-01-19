'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { format, subDays, startOfMonth, endOfMonth } from 'date-fns';
import { FileSpreadsheet, Download, Loader2, Calendar } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { api } from '@/lib/api';
import { toast } from 'sonner';

export default function ExportPage() {
    // Default to current month
    const [startDate, setStartDate] = useState(format(startOfMonth(new Date()), 'yyyy-MM-dd'));
    const [endDate, setEndDate] = useState(format(endOfMonth(new Date()), 'yyyy-MM-dd'));
    const [isExporting, setIsExporting] = useState(false);

    // Fetch Stats
    const { data: stats, isLoading: isLoadingStats } = useQuery({
        queryKey: ['export-stats', startDate, endDate],
        queryFn: async () => {
            const res = await api.get(`/leaves/export/stats?start_date=${startDate}&end_date=${endDate}`);
            return res.data;
        },
        enabled: !!startDate && !!endDate
    });

    const handleExport = async () => {
        setIsExporting(true);
        try {
            // Trigger download via direct URL to handle blob/stream easily
            const token = localStorage.getItem('token'); // Assuming simple token storage or adjust if httponly
            // Actually, we should try using Axios response type blob, but direct link with token in auth header is tricky if not cookie.
            // Using Axios is better for Auth.

            const response = await api.get(`/leaves/export?start_date=${startDate}&end_date=${endDate}`, {
                responseType: 'blob'
            });

            // Create blob link to download
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `leave_report_${startDate}_${endDate}.csv`);
            document.body.appendChild(link);
            link.click();
            link.remove();

            toast.success("Report downloaded successfully");
        } catch (error) {
            toast.error("Failed to download report");
            console.error(error);
        } finally {
            setIsExporting(false);
        }
    };

    return (
        <div className="space-y-8 max-w-4xl mx-auto">
            <div className="flex justify-between items-end">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-50">Leave Reports</h1>
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                        Export approved leave data for reporting.
                    </p>
                </div>
            </div>

            <div className="grid gap-6 md:grid-cols-3">
                {/* Configuration Card */}
                <Card className="md:col-span-2">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Calendar className="w-5 h-5 text-blue-600" />
                            Select Period
                        </CardTitle>
                        <CardDescription>
                            Choose the date range for the payroll cycle.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="start">Start Date</Label>
                                <Input
                                    id="start"
                                    type="date"
                                    value={startDate}
                                    onChange={(e) => setStartDate(e.target.value)}
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="end">End Date</Label>
                                <Input
                                    id="end"
                                    type="date"
                                    value={endDate}
                                    onChange={(e) => setEndDate(e.target.value)}
                                />
                            </div>
                        </div>

                        <div className="flex gap-2">
                            <Button variant="outline" size="sm" onClick={() => {
                                const today = new Date();
                                setStartDate(format(startOfMonth(subDays(today, 30)), 'yyyy-MM-dd'));
                                setEndDate(format(endOfMonth(subDays(today, 30)), 'yyyy-MM-dd'));
                            }}>
                                Last Month
                            </Button>
                            <Button variant="outline" size="sm" onClick={() => {
                                const today = new Date();
                                setStartDate(format(startOfMonth(today), 'yyyy-MM-dd'));
                                setEndDate(format(endOfMonth(today), 'yyyy-MM-dd'));
                            }}>
                                This Month
                            </Button>
                        </div>
                    </CardContent>
                </Card>

                {/* Summary Card */}
                <Card className="bg-slate-50 dark:bg-slate-900/20 border-blue-200 dark:border-blue-900/30">
                    <CardHeader>
                        <CardTitle className="text-lg">Summary</CardTitle>
                        <CardDescription>Records found</CardDescription>
                    </CardHeader>
                    <CardContent>
                        {isLoadingStats ? (
                            <div className="flex justify-center py-4">
                                <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
                            </div>
                        ) : (
                            <div className="space-y-4">
                                <div>
                                    <div className="text-3xl font-bold text-slate-900 dark:text-slate-50">
                                        {stats?.total_records || 0}
                                    </div>
                                    <div className="text-xs text-slate-500">Total Approved Records</div>
                                </div>
                                <div className="space-y-1 pt-2 border-t border-slate-200 dark:border-slate-800">
                                    <div className="flex justify-between text-sm">
                                        <span className="text-slate-500">Leave Requests</span>
                                        <span className="font-medium">{stats?.leaves_count || 0}</span>
                                    </div>
                                    <div className="flex justify-between text-sm">
                                        <span className="text-slate-500">Comp-Off Grants</span>
                                        <span className="font-medium">{stats?.comp_off_count || 0}</span>
                                    </div>
                                </div>
                            </div>
                        )}
                    </CardContent>
                    <CardFooter>
                        <Button
                            className="w-full bg-green-600 hover:bg-green-700"
                            onClick={handleExport}
                            disabled={isExporting || isLoadingStats || !stats?.total_records}
                        >
                            {isExporting ? (
                                <Loader2 className="w-4 h-4 animate-spin mr-2" />
                            ) : (
                                <Download className="w-4 h-4 mr-2" />
                            )}
                            Download CSV
                        </Button>
                    </CardFooter>
                </Card>
            </div>
        </div>
    );
}
