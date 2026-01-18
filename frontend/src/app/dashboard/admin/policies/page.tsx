'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import { toast } from 'sonner';
import { Loader2, Save, Upload, FileText, Trash2, ShieldCheck, Eye, Search, CheckCircle2, XCircle } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
} from '@/components/ui/dialog';

interface LeavePolicy {
    year: number;
    casual_leave_quota: number;
    sick_leave_quota: number;
    wfh_quota: number;
    is_active: boolean;
    _id?: string;
    document_url?: string;
    document_name?: string;
    documents?: Array<{
        name: string;
        url: string;
        uploaded_at: string;
    }>;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function PoliciesPage() {
    const [policies, setPolicies] = useState<LeavePolicy[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [isUploading, setIsUploading] = useState(false);

    // Form State
    const [year, setYear] = useState<number>(new Date().getFullYear());
    const [casualQuota, setCasualQuota] = useState<number>(12);
    const [sickQuota, setSickQuota] = useState<number>(5);
    const [wfhQuota, setWfhQuota] = useState<number>(2);

    const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
    const [docName, setDocName] = useState<string>('');

    // Report State
    const [reportYear, setReportYear] = useState<number | null>(null);
    const [ackReport, setAckReport] = useState<any[]>([]);
    const [isReportLoading, setIsReportLoading] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');

    useEffect(() => {
        fetchPolicies();
    }, []);

    const fetchPolicies = async () => {
        try {
            const token = localStorage.getItem('access_token');
            const res = await fetch(`${API_URL}/policies/`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                setPolicies(data);
            }
        } catch (error) {
            console.error("Failed to fetch policies", error);
        } finally {
            setIsLoading(false);
        }
    };

    const fetchAckReport = async (year: number) => {
        setReportYear(year);
        setIsReportLoading(true);
        try {
            const token = localStorage.getItem('access_token');
            const res = await fetch(`${API_URL}/policies/${year}/report`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                setAckReport(data);
            }
        } catch (error) {
            toast.error("Failed to fetch acknowledgment report");
        } finally {
            setIsReportLoading(false);
        }
    };

    const handleSavePolicy = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSaving(true);

        try {
            const token = localStorage.getItem('access_token');
            const res = await fetch(`${API_URL}/policies/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    year: year,
                    casual_leave_quota: casualQuota,
                    sick_leave_quota: sickQuota,
                    wfh_quota: wfhQuota,
                    is_active: true
                })
            });

            if (!res.ok) {
                throw new Error('Failed to save policy');
            }

            toast.success(`Policy quotas for ${year} saved.`);
            await fetchPolicies();
        } catch (error: any) {
            toast.error("Failed to save policy");
        } finally {
            setIsSaving(false);
        }
    };

    const handleUploadDocument = async () => {
        if (selectedFiles.length === 0) return;

        setIsUploading(true);
        try {
            const token = localStorage.getItem('access_token');

            // Upload files sequentially
            for (const file of selectedFiles) {
                const formData = new FormData();
                formData.append('file', file);

                const url = new URL(`${API_URL}/policies/${year}/document`);
                // If only one file is selected, use the custom label if provided
                if (selectedFiles.length === 1 && docName) {
                    url.searchParams.append('name', docName);
                }

                const res = await fetch(url.toString(), {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`
                    },
                    body: formData
                });

                if (!res.ok) {
                    throw new Error(`Failed to upload ${file.name}`);
                }
            }

            toast.success(`${selectedFiles.length} document(s) uploaded successfully`);
            await fetchPolicies();
            setSelectedFiles([]);
            setDocName('');
        } catch (error: any) {
            toast.error(error.message || "Failed to upload document");
        } finally {
            setIsUploading(false);
        }
    };

    const handleDeleteDocument = async (policyYear: number, docUrl: string) => {
        if (!confirm("Are you sure you want to delete this document?")) return;

        try {
            const token = localStorage.getItem('access_token');
            const res = await fetch(`${API_URL}/policies/${policyYear}/document?url=${encodeURIComponent(docUrl)}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!res.ok) {
                throw new Error("Failed to delete document");
            }

            toast.success("Document deleted");
            await fetchPolicies();
        } catch (error: any) {
            toast.error(error.message || "Failed to delete document");
        }
    };

    const handleDeletePolicy = async (year: number) => {
        if (!confirm(`Are you sure you want to delete the entire policy for ${year}? This will also delete all associated documents.`)) return;

        try {
            const token = localStorage.getItem('access_token');
            const res = await fetch(`${API_URL}/policies/${year}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!res.ok) {
                throw new Error("Failed to delete policy");
            }

            toast.success(`Policy for ${year} deleted`);
            await fetchPolicies();
        } catch (error: any) {
            toast.error(error.message || "Failed to delete policy");
        }
    };

    const filteredReport = ackReport.filter(r =>
        r.full_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        r.email?.toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-50">Policy Management</h1>
            <p className="text-slate-500">Configure yearly leave policies and upload official documents.</p>

            <div className="grid gap-6 md:grid-cols-2">

                {/* Left Column: Configuration Forms */}
                <div className="space-y-6">

                    {/* Card 1: Quotas */}
                    <Card>
                        <CardHeader>
                            <CardTitle>Leave Policy</CardTitle>
                            <CardDescription>Set quotas for the year {year}.</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <form onSubmit={handleSavePolicy} className="space-y-4">
                                <div className="space-y-2">
                                    <Label htmlFor="year">Year</Label>
                                    <Input
                                        id="year"
                                        type="number"
                                        value={year}
                                        onChange={(e) => {
                                            const val = parseInt(e.target.value);
                                            setYear(isNaN(val) ? 0 : val);
                                        }}
                                        required
                                        min={2024}
                                        max={2100}
                                    />
                                </div>

                                <div className="grid grid-cols-3 gap-4">
                                    <div className="space-y-2">
                                        <Label htmlFor="cl">Casual Leave</Label>
                                        <Input
                                            id="cl"
                                            type="number"
                                            value={casualQuota}
                                            onChange={(e) => {
                                                const val = parseInt(e.target.value);
                                                setCasualQuota(isNaN(val) ? 0 : val);
                                            }}
                                            required
                                            min={0}
                                        />
                                        <p className="text-xs text-slate-500">Accrued monthly</p>
                                    </div>
                                    <div className="space-y-2">
                                        <Label htmlFor="sl">Sick Leave</Label>
                                        <Input
                                            id="sl"
                                            type="number"
                                            value={sickQuota}
                                            onChange={(e) => {
                                                const val = parseInt(e.target.value);
                                                setSickQuota(isNaN(val) ? 0 : val);
                                            }}
                                            required
                                            min={0}
                                        />
                                        <p className="text-xs text-slate-500">Flat allocation</p>
                                    </div>
                                    <div className="space-y-2">
                                        <Label htmlFor="wfh">WFH</Label>
                                        <Input
                                            id="wfh"
                                            type="number"
                                            value={wfhQuota}
                                            onChange={(e) => {
                                                const val = parseInt(e.target.value);
                                                setWfhQuota(isNaN(val) ? 0 : val);
                                            }}
                                            required
                                            min={0}
                                        />
                                        <p className="text-xs text-slate-500">Flat allocation</p>
                                    </div>
                                </div>

                                <Button type="submit" disabled={isSaving} className="w-full">
                                    {isSaving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
                                    Save Policy
                                </Button>
                            </form>
                        </CardContent>
                    </Card>

                    {/* Card 2: Document Upload */}
                    <Card>
                        <CardHeader>
                            <CardTitle>Policy Document</CardTitle>
                            <CardDescription>Upload the official PDF for {year}.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="space-y-2">
                                <Label htmlFor="policy-doc">Statement / Policy PDF</Label>
                                <Input
                                    id="policy-doc"
                                    type="file"
                                    accept="application/pdf"
                                    multiple
                                    onChange={(e) => {
                                        const files = e.target.files ? Array.from(e.target.files) : [];
                                        setSelectedFiles(files);
                                    }}
                                />
                                {selectedFiles.length > 0 && (
                                    <div className="space-y-1">
                                        <div className="flex justify-between items-center">
                                            <p className="text-xs font-medium text-blue-600">Selected ({selectedFiles.length}):</p>
                                            <button
                                                onClick={() => setSelectedFiles([])}
                                                className="text-[10px] text-red-500 hover:underline"
                                            >
                                                Clear Selection
                                            </button>
                                        </div>
                                        <ul className="text-[10px] text-slate-500 list-disc pl-4 max-h-20 overflow-y-auto">
                                            {selectedFiles.map((f, i) => (
                                                <li key={i} className="truncate">{f.name}</li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </div>
                            {selectedFiles.length === 1 && (
                                <div className="space-y-2">
                                    <Label htmlFor="doc-name">Document Label (e.g. Leave Policy)</Label>
                                    <Input
                                        id="doc-name"
                                        type="text"
                                        placeholder="Leave Policy / Holiday List..."
                                        value={docName}
                                        onChange={(e) => setDocName(e.target.value)}
                                    />
                                </div>
                            )}
                            <Button
                                onClick={handleUploadDocument}
                                disabled={isUploading || selectedFiles.length === 0}
                                variant="secondary"
                                className="w-full"
                            >
                                {isUploading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />}
                                {selectedFiles.length > 1 ? `Upload ${selectedFiles.length} Documents` : 'Upload Document'}
                            </Button>
                        </CardContent>
                    </Card>

                </div>

                {/* Right Column: Existing Policies */}
                <div className="space-y-6">
                    {/* Card 3: Leave Quotas History */}
                    <Card>
                        <CardHeader>
                            <CardTitle>Leave Quotas</CardTitle>
                        </CardHeader>
                        <CardContent>
                            {isLoading ? (
                                <div className="flex justify-center p-4"><Loader2 className="animate-spin" /></div>
                            ) : policies.length === 0 ? (
                                <p className="text-center text-slate-500 py-4">No policies found.</p>
                            ) : (
                                <Table>
                                    <TableHeader>
                                        <TableRow>
                                            <TableHead>Year</TableHead>
                                            <TableHead>CL / SL / WFH</TableHead>
                                            <TableHead className="w-[100px]"></TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {policies.map((policy) => (
                                            <TableRow key={policy._id} className="group">
                                                <TableCell className="font-medium align-top">
                                                    <div className="flex items-center">
                                                        {policy.year}
                                                        {policy.year === new Date().getFullYear() && (
                                                            <Badge variant="outline" className="ml-2 text-xs border-green-500 text-green-500">Active</Badge>
                                                        )}
                                                    </div>
                                                </TableCell>
                                                <TableCell className="align-top">
                                                    <div className="text-sm">
                                                        <span className="font-semibold">{policy.casual_leave_quota}</span> CL /
                                                        <span className="font-semibold"> {policy.sick_leave_quota}</span> SL /
                                                        <span className="font-semibold"> {policy.wfh_quota}</span> WFH
                                                    </div>
                                                </TableCell>
                                                <TableCell className="align-top">
                                                    <div className="flex items-center gap-1">
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            onClick={() => fetchAckReport(policy.year)}
                                                            className="h-8 w-8 p-0 text-blue-500 hover:text-blue-700 hover:bg-blue-50 opacity-0 group-hover:opacity-100 transition-opacity"
                                                            title="View Acknowledgment Report"
                                                        >
                                                            <ShieldCheck className="h-4 w-4" />
                                                        </Button>
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            onClick={() => handleDeletePolicy(policy.year)}
                                                            className="h-8 w-8 p-0 text-red-500 hover:text-red-700 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-opacity"
                                                            title="Delete Policy"
                                                        >
                                                            <Trash2 className="h-4 w-4" />
                                                        </Button>
                                                    </div>
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            )}
                        </CardContent>
                    </Card>

                    {/* Card 4: Document Policies History */}
                    <Card>
                        <CardHeader>
                            <CardTitle>Policy Documents</CardTitle>
                        </CardHeader>
                        <CardContent>
                            {isLoading ? (
                                <div className="flex justify-center p-4"><Loader2 className="animate-spin" /></div>
                            ) : policies.length === 0 ? (
                                <p className="text-center text-slate-500 py-4">No policies found.</p>
                            ) : (
                                <Table>
                                    <TableHeader>
                                        <TableRow>
                                            <TableHead>Year</TableHead>
                                            <TableHead>Documents</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {policies.map((policy) => (
                                            <TableRow key={`doc-${policy._id}`}>
                                                <TableCell className="font-medium align-top">
                                                    {policy.year}
                                                </TableCell>
                                                <TableCell className="align-top">
                                                    <div className="space-y-2">
                                                        {policy.documents && policy.documents.length > 0 ? (
                                                            policy.documents.map((doc, idx) => (
                                                                <div key={idx} className="flex items-center justify-between group">
                                                                    <a
                                                                        href={`${API_URL}${doc.url}`}
                                                                        target="_blank"
                                                                        rel="noopener noreferrer"
                                                                        className="inline-flex items-center text-blue-600 hover:underline text-sm"
                                                                    >
                                                                        <FileText className="w-4 h-4 mr-2" />
                                                                        {doc.name}
                                                                    </a>
                                                                    <Button
                                                                        variant="ghost"
                                                                        size="sm"
                                                                        onClick={() => handleDeleteDocument(policy.year, doc.url)}
                                                                        className="h-8 w-8 p-0 text-red-500 hover:text-red-700 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-opacity"
                                                                    >
                                                                        <Trash2 className="h-4 w-4" />
                                                                    </Button>
                                                                </div>
                                                            ))
                                                        ) : policy.document_url ? (
                                                            // Fallback for legacy items not yet migrated to documents list
                                                            <div className="flex items-center justify-between group">
                                                                <a
                                                                    href={`${API_URL}${policy.document_url}`}
                                                                    target="_blank"
                                                                    rel="noopener noreferrer"
                                                                    className="inline-flex items-center text-blue-600 hover:underline text-sm"
                                                                >
                                                                    <FileText className="w-4 h-4 mr-2" />
                                                                    {policy.document_name || "Official Policy"}
                                                                </a>
                                                            </div>
                                                        ) : (
                                                            <span className="text-slate-400 text-xs italic">No documents uploaded</span>
                                                        )}
                                                    </div>
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            )}
                        </CardContent>
                    </Card>
                </div>
            </div>

            {/* Acknowledgment Report Dialog */}
            <Dialog open={reportYear !== null} onOpenChange={(open) => !open && setReportYear(null)}>
                <DialogContent className="max-w-3xl max-h-[90vh] flex flex-col">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <ShieldCheck className="w-5 h-5 text-blue-600" />
                            Acknowledgment Report - {reportYear}
                        </DialogTitle>
                        <DialogDescription>
                            List of all active employees and their policy acknowledgment status for {reportYear}.
                        </DialogDescription>
                    </DialogHeader>

                    <div className="relative mt-4">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                        <Input
                            placeholder="Search employee by name or email..."
                            className="pl-9"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                    </div>

                    <div className="flex-1 overflow-auto mt-4 border rounded-lg">
                        <Table>
                            <TableHeader className="bg-slate-50 sticky top-0">
                                <TableRow>
                                    <TableHead>Employee</TableHead>
                                    <TableHead>Status</TableHead>
                                    <TableHead>Acknowledged At</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {isReportLoading ? (
                                    <TableRow>
                                        <TableCell colSpan={3} className="text-center py-8">
                                            <Loader2 className="h-6 w-6 animate-spin mx-auto text-slate-400" />
                                            <p className="text-sm text-slate-500 mt-2">Loading report...</p>
                                        </TableCell>
                                    </TableRow>
                                ) : filteredReport.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={3} className="text-center py-8 text-slate-500">
                                            No employees found matching your search.
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    filteredReport.map((row) => (
                                        <TableRow key={row.user_id}>
                                            <TableCell>
                                                <div className="font-medium text-slate-900">{row.full_name}</div>
                                                <div className="text-xs text-slate-500">{row.email}</div>
                                            </TableCell>
                                            <TableCell>
                                                {row.fully_acknowledged ? (
                                                    <Badge className="bg-green-100 text-green-700 hover:bg-green-100 border-green-200">
                                                        <CheckCircle2 className="w-3 h-3 mr-1" />
                                                        Complete
                                                    </Badge>
                                                ) : row.acknowledged_count > 0 ? (
                                                    <Badge variant="secondary" className="bg-amber-100 text-amber-700 border-amber-200">
                                                        <Loader2 className="w-3 h-3 mr-1" />
                                                        Partial ({row.acknowledged_count}/{row.total_documents})
                                                    </Badge>
                                                ) : (
                                                    <Badge variant="secondary" className="bg-slate-100 text-slate-500 border-slate-200">
                                                        <XCircle className="w-3 h-3 mr-1" />
                                                        Pending
                                                    </Badge>
                                                )}
                                            </TableCell>
                                            <TableCell>
                                                <div className="text-xs space-y-1">
                                                    {row.acknowledgments.length > 0 ? (
                                                        row.acknowledgments.map((ack: any, i: number) => {
                                                            const docName = policies.find(p => p.year === reportYear)?.documents?.find(d => d.url === ack.document_url)?.name || "Document";
                                                            return (
                                                                <div key={i} className="flex items-center gap-1 text-slate-600">
                                                                    <CheckCircle2 className="w-2.5 h-2.5 text-green-500" />
                                                                    <span>{docName}</span>
                                                                    <span className="text-[10px] text-slate-400">({new Date(ack.acknowledged_at).toLocaleDateString()})</span>
                                                                </div>
                                                            );
                                                        })
                                                    ) : (
                                                        <span className="text-slate-400 font-italic">No documents read</span>
                                                    )}
                                                </div>
                                            </TableCell>
                                        </TableRow>
                                    ))
                                )}
                            </TableBody>
                        </Table>
                    </div>
                    <div className="flex justify-between items-center mt-4 text-xs text-slate-500">
                        <div>Showing {filteredReport.length} employees</div>
                        <div className="flex gap-4">
                            <div className="flex items-center gap-1.5">
                                <div className="w-2 h-2 rounded-full bg-green-500" />
                                <span>{ackReport.filter(r => r.fully_acknowledged).length} Complete</span>
                            </div>
                            <div className="flex items-center gap-1.5">
                                <div className="w-2 h-2 rounded-full bg-amber-500" />
                                <span>{ackReport.filter(r => !r.fully_acknowledged && r.acknowledged_count > 0).length} Partial</span>
                            </div>
                            <div className="flex items-center gap-1.5">
                                <div className="w-2 h-2 rounded-full bg-slate-300" />
                                <span>{ackReport.filter(r => r.acknowledged_count === 0).length} Pending</span>
                            </div>
                        </div>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
}
