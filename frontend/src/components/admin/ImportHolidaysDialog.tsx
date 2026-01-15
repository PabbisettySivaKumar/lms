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
            transformHeader: (header) => header.toLowerCase().trim(), // Normalize headers
            complete: (results) => {
                try {
                    const validData: ParsedHoliday[] = [];
                    const errors: string[] = [];

                    results.data.forEach((row, index) => {
                        const keys = Object.keys(row);

                        // Map flexible column names
                        // We look for keys that *contain* our target words (case insensitive is handled by transformHeader)
                        // transformed header matches: 's.no', 'date', 'day', 'holiday'

                        let dateVal = row.date || row.Date || row['date'] || null;
                        let nameVal = row.name || row.Name || row.holiday || row['holiday'] || row['event name'] || null;
                        let optionalVal = row.optional || row.Optional || row.is_optional || 'false';

                        // Specific handling for the User's provided format: "S.No, Date, Day, Holiday"
                        if (!dateVal && keys.includes('date')) dateVal = row['date'];
                        if (!nameVal && keys.includes('holiday')) nameVal = row['holiday'];


                        // Fallback: Handle single column issue (e.g. "date,name" in one cell)
                        if (!dateVal && !nameVal && keys.length === 1) {
                            const singleKey = keys[0];
                            const singleValue = row[singleKey];

                            // Check if the key itself looks like a combined header "date,name"
                            // or if we just have a single value that needs splitting
                            if (typeof singleValue === 'string' && singleValue.includes(',')) {
                                const parts = singleValue.split(',');
                                // Assume order: date, name, optional OR s.no, date, day, holiday
                                // If 4 parts, likely User's format: 1, 14 Jan 2026, Wednesday, Makara Sankranti
                                if (parts.length >= 4) {
                                    dateVal = parts[1]?.trim();
                                    nameVal = parts[3]?.trim();
                                    // part 0 is s.no, part 2 is day
                                } else {
                                    dateVal = parts[0]?.trim();
                                    nameVal = parts[1]?.trim();
                                    if (parts.length > 2) optionalVal = parts[2]?.trim();
                                }
                            }
                        }

                        // Basic Validation
                        if (!dateVal || !nameVal) {
                            // Only report if row is not completely empty (papaparse handles skipEmptyLines strictly, but sometimes whitespace remains)
                            const values = Object.values(row).join('').trim();
                            if (values.length > 0) {
                                errors.push(`Row ${index + 2}: Missing Date or Name/Holiday`);
                            }
                            return;
                        }

                        // Sanitize inputs (handle newlines from messy excel copy-paste)
                        let cleanDate = dateVal.toString().replace(/\n/g, ' ').trim();
                        const cleanName = nameVal.toString().replace(/\n/g, ' ').trim();

                        // Date Parsing Logic
                        // Supports: YYYY-MM-DD, DD-MM-YYYY, DD MMM YYYY (e.g., 14 Jan 2026)
                        let parsedDateStr = '';

                        // Try Standard ISO YYYY-MM-DD
                        if (/^\d{4}-\d{2}-\d{2}$/.test(cleanDate)) {
                            parsedDateStr = cleanDate;
                        }
                        // Try "14 Jan 2026" or "14-Jan-2026"
                        else {
                            try {
                                const { parse, format: formatDate } = require('date-fns');
                                // Try common formats
                                const formatsToTry = ['d MMM yyyy', 'dd MMM yyyy', 'dd-MMM-yyyy', 'd-MMM-yyyy', 'yyyy/MM/dd', 'dd/MM/yyyy'];
                                let validDate = null;

                                for (const fmt of formatsToTry) {
                                    const d = parse(cleanDate, fmt, new Date());
                                    if (!isNaN(d.getTime())) {
                                        validDate = d;
                                        break;
                                    }
                                }

                                if (validDate) {
                                    parsedDateStr = formatDate(validDate, 'yyyy-MM-dd');
                                }
                            } catch (e) {
                                // console.error(e);
                            }
                        }

                        if (!parsedDateStr) {
                            errors.push(`Row ${index + 2}: Invalid date format '${cleanDate}'. Supported: YYYY-MM-DD, 14 Jan 2026`);
                            return;
                        }

                        const yearVal = parseInt(parsedDateStr.split('-')[0]);

                        validData.push({
                            date: parsedDateStr,
                            name: cleanName,
                            is_optional: optionalVal?.toString().toLowerCase() === 'true',
                            year: yearVal
                        });
                    });

                    if (errors.length > 0) {
                        setError(`Found ${errors.length} errors. First error: ${errors[0]}`);
                    } else if (validData.length === 0) {
                        setError("No valid records found in file.");
                    } else {
                        setParsedData(validData);
                    }
                } catch (err) {
                    setError("Failed to parse CSV file.");
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
                // Handle Pydantic validation errors (array of objects)
                // e.g. [{loc:..., msg:..., type:...}]
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
