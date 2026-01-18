'use client';

import { useState, useRef } from 'react';
import Papa from 'papaparse';
import { Upload, Download, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';
import { toast } from 'sonner';
import { useQueryClient } from '@tanstack/react-query';

import api from '@/lib/axios';
import { Button } from '@/components/ui/button';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import { Alert, AlertDescription, AlertTitle } from '../ui/alert';

interface ImportHolidaysDialogProps {
    isOpen: boolean;
    onClose: () => void;
}

interface HolidayCSVRow {
    Date: string;
    Name: string;
    Optional: string; // "true" or "false"
}

interface ParsedHoliday {
    date: string; // YYYY-MM-DD
    name: string;
    is_optional: boolean;
    year: number;
}

export function ImportHolidaysDialog({ isOpen, onClose }: ImportHolidaysDialogProps) {
    const [parsedData, setParsedData] = useState<ParsedHoliday[]>([]);
    const [isParsing, setIsParsing] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const queryClient = useQueryClient();

    const resetState = () => {
        setParsedData([]);
        setError(null);
        if (fileInputRef.current) fileInputRef.current.value = '';
    };

    const handleClose = () => {
        resetState();
        onClose();
    };

    const downloadTemplate = () => {
        const csvContent = "Date,Name,Optional\n2026-01-26,Republic Day,false\n2026-03-25,Holi,true";
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement("a");
        const url = URL.createObjectURL(blob);
        link.setAttribute("href", url);
        link.setAttribute("download", "holidays_template.csv");
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setError(null);
        setIsParsing(true);

        Papa.parse<any>(file, {
            header: true,
            skipEmptyLines: true,
            transformHeader: (header) => header.toLowerCase().trim(),
            complete: (results) => {
                try {
                    const validData: ParsedHoliday[] = [];
                    const errors: string[] = [];
                    const processedDates = new Set<string>(); // Deduplication

                    results.data.forEach((row, index) => {
                        const keys = Object.keys(row);

                        let dateVal = row.date || row.Date || row['date'] || null;
                        let nameVal = row.name || row.Name || row.holiday || row['holiday'] || row['event name'] || null;
                        let optionalVal = row.optional || row.Optional || row.is_optional || 'false';

                        if (!dateVal && keys.includes('date')) dateVal = row['date'];
                        if (!nameVal && keys.includes('holiday')) nameVal = row['holiday'];

                        // Fallback logic for weird CSV mapping (same as before)
                        if (!dateVal && !nameVal && keys.length === 1) {
                            const singleKey = keys[0];
                            const singleValue = row[singleKey];
                            if (typeof singleValue === 'string' && singleValue.includes(',')) {
                                const parts = singleValue.split(',');
                                if (parts.length >= 4) {
                                    dateVal = parts[1]?.trim();
                                    nameVal = parts[3]?.trim();
                                } else {
                                    dateVal = parts[0]?.trim();
                                    nameVal = parts[1]?.trim();
                                    if (parts.length > 2) optionalVal = parts[2]?.trim();
                                }
                            }
                        }

                        if (!dateVal || !nameVal) {
                            const values = Object.values(row).join('').trim();
                            if (values.length > 0) {
                                errors.push(`Row ${index + 2}: Missing Date or Name`);
                            }
                            return;
                        }

                        // Sanitize
                        let cleanDate = dateVal.toString().replace(/\n/g, ' ').trim();
                        // Normalize month casing (e.g., "jan" -> "Jan") just in case
                        // cleanDate = cleanDate.charAt(0).toUpperCase() + cleanDate.slice(1); 
                        // Actually hard to blindly titlecase if it starts with number. Let parse handle it.

                        const cleanName = nameVal.toString().replace(/\n/g, ' ').trim();

                        let parsedDateStr = '';

                        // 1. Try ISO
                        if (/^\d{4}-\d{2}-\d{2}$/.test(cleanDate)) {
                            parsedDateStr = cleanDate;
                        } else {
                            try {
                                const { parse, format: formatDate } = require('date-fns');
                                // Added support for "Jan 14th 26", "Jan 14 26", etc.
                                const formatsToTry = [
                                    'd MMM yyyy', 'dd MMM yyyy', 'dd-MMM-yyyy', 'd-MMM-yyyy',
                                    'dd-MMM-yy', 'd-MMM-yy', // Support 14-Jan-26
                                    'd MMM yy', 'dd MMM yy', // Support 14 Jan 26
                                    'yyyy/MM/dd', 'dd/MM/yyyy',
                                    'MMM do yy', 'MMM do yyyy', 'MMM d yy', 'MMM d yyyy',
                                    'do MMM yy', 'do MMM yyyy'
                                ];
                                let validDate = null;

                                for (const fmt of formatsToTry) {
                                    // Handle cases where the year might be 2 digits (yy) -> 1926 or 2026? 
                                    // date-fns maps 0-68 to 2000-2068 by default usually, but we need caution.

                                    // Pre-processing for "Jan 14th 26" -> remove "th", "st", "nd", "rd" if pattern doesn't catch it?
                                    // actually 'do' pattern catches it.

                                    const d = parse(cleanDate, fmt, new Date());
                                    if (!isNaN(d.getTime())) {
                                        // Sanity check year
                                        const y = d.getFullYear();
                                        if (y > 1900 && y < 2100) {
                                            validDate = d;
                                            break;
                                        }
                                    }
                                }

                                if (validDate) {
                                    parsedDateStr = formatDate(validDate, 'yyyy-MM-dd');
                                }
                            } catch (e) { }
                        }

                        if (!parsedDateStr) {
                            errors.push(`Row ${index + 2}: Invalid date '${cleanDate}'`);
                            return;
                        }

                        // Deduplication: Check if we already processed this date in this batch
                        if (processedDates.has(parsedDateStr)) {
                            // Skip silently or log? User asked to fix redundancies. 
                            // Skipping ensures unique dates.
                            return;
                        }
                        processedDates.add(parsedDateStr);

                        const yearVal = parseInt(parsedDateStr.split('-')[0]);

                        validData.push({
                            date: parsedDateStr,
                            name: cleanName,
                            is_optional: optionalVal?.toString().toLowerCase() === 'true',
                            year: yearVal
                        });
                    });

                    if (errors.length > 0) {
                        setError(`Found ${errors.length} errors. First: ${errors[0]}`);
                    } else if (validData.length === 0) {
                        setError("No valid records found.");
                    } else {
                        setParsedData(validData);
                        if (processedDates.size < results.data.length) {
                            // Maybe hint that some were ignored?
                            // toast.info(`Ignored ${results.data.length - processedDates.size} duplicate entries.`);
                        }
                    }
                } catch (err) {
                    setError("Failed to parse CSV.");
                } finally {
                    setIsParsing(false);
                }
            },
            error: (err) => {
                setError(`CSV Usage Error: ${err.message}`);
                setIsParsing(false);
            }
        });
    };

    const handleImport = async () => {
        if (parsedData.length === 0) return;

        setIsUploading(true);
        try {
            const res = await api.post('/admin/holidays/bulk', parsedData);
            if (res.data.success) {
                toast.success(`Successfully imported ${res.data.count} holidays!`);
                if (res.data.errors && res.data.errors.length > 0) {
                    toast.warning(`Skipped ${res.data.errors.length} duplicates.`);
                }
                queryClient.invalidateQueries({ queryKey: ['holidays'] });
                queryClient.invalidateQueries({ queryKey: ['calendar-holidays'] });
                handleClose();
            }
        } catch (error: any) {
            const detail = error.response?.data?.detail;
            let errorMessage = "Import failed";

            if (typeof detail === 'string') {
                errorMessage = detail;
            } else if (Array.isArray(detail)) {
                errorMessage = detail.map((err: any) => err.msg).join(', ');
            } else if (typeof detail === 'object' && detail !== null) {
                errorMessage = JSON.stringify(detail);
            }

            toast.error(errorMessage);
        } finally {
            setIsUploading(false);
        }
    };

    return (
        <Dialog open={isOpen} onOpenChange={handleClose}>
            <DialogContent className="sm:max-w-[600px]">
                <DialogHeader>
                    <DialogTitle>Import Holidays (CSV)</DialogTitle>
                    <DialogDescription>
                        Bulk upload holidays using a CSV file. Dates must be in YYYY-MM-DD format.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-4">
                    {/* Actions */}
                    <div className="flex items-center gap-4">
                        <Button variant="outline" size="sm" onClick={downloadTemplate}>
                            <Download className="mr-2 h-4 w-4" />
                            Download Template
                        </Button>
                        <div className="relative">
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept=".csv"
                                className="absolute inset-0 opacity-0 cursor-pointer w-full"
                                onChange={handleFileChange}
                                disabled={isUploading || isParsing}
                            />
                            <Button size="sm">
                                <Upload className="mr-2 h-4 w-4" />
                                Select CSV File
                            </Button>
                        </div>
                    </div>

                    {/* Status / Errors */}
                    {isParsing && (
                        <div className="flex items-center text-sm text-slate-500">
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Parsing file...
                        </div>
                    )}

                    {error && (
                        <Alert variant="destructive">
                            <AlertCircle className="h-4 w-4" />
                            <AlertTitle>Error</AlertTitle>
                            <AlertDescription>{error}</AlertDescription>
                        </Alert>
                    )}

                    {/* Preview Table */}
                    {parsedData.length > 0 && !error && (
                        <div className="rounded-md border max-h-[300px] overflow-auto">
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead>Date</TableHead>
                                        <TableHead>Event Name</TableHead>
                                        <TableHead>Type</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {parsedData.map((row, i) => (
                                        <TableRow key={i}>
                                            <TableCell>{row.date}</TableCell>
                                            <TableCell>{row.name}</TableCell>
                                            <TableCell>
                                                {row.is_optional ? (
                                                    <span className="text-blue-600 text-xs bg-blue-50 px-2 py-0.5 rounded">Optional</span>
                                                ) : (
                                                    <span className="text-slate-600 text-xs bg-slate-100 px-2 py-0.5 rounded">Public</span>
                                                )}
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                            <div className="p-2 bg-slate-50 border-t text-xs text-center text-slate-500">
                                Showing {parsedData.length} record(s) ready to import.
                            </div>
                        </div>
                    )}
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={handleClose} disabled={isUploading}>
                        Cancel
                    </Button>
                    <Button onClick={handleImport} disabled={parsedData.length === 0 || isUploading}>
                        {isUploading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Import {parsedData.length > 0 ? `${parsedData.length} Holidays` : ''}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
