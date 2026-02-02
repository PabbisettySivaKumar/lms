'use client';

import { useState, useMemo, useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
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
import api from '@/lib/axios';
import { useMutationWithToast } from '@/hooks/useMutationWithToast';
import { LoadingSpinner } from '@/components/common/LoadingSpinner';
import { ConfirmDialog } from '@/components/common/ConfirmDialog';

interface LeavePolicy {
    id?: number; // Backend returns integer ID
    year: number;
    casual_leave_quota: number;
    sick_leave_quota: number;
    wfh_quota: number;
    is_active: boolean;
    _id?: string; // Backward compatibility
    documents?: Array<{
        id?: number;
        policy_id?: number;
        name: string;
        url: string;
        uploaded_at?: string;
    }>;
}

export default function PoliciesPage() {
    const queryClient = useQueryClient();
    
    // Form State
    const [year, setYear] = useState<number>(new Date().getFullYear());
    const [casualQuota, setCasualQuota] = useState<number>(12);
    const [sickQuota, setSickQuota] = useState<number>(5);
    const [wfhQuota, setWfhQuota] = useState<number>(2);

    const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
    const [docName, setDocName] = useState<string>('');

    // Report State
    const [reportYear, setReportYear] = useState<number | null>(null);
    const [searchQuery, setSearchQuery] = useState('');

    // Fetch policies using React Query
    const { data: policiesData = [], isLoading } = useQuery<LeavePolicy[]>({
        queryKey: ['policies'],
        queryFn: async () => {
            try {
                const response = await api.get('/policies/', {
                    headers: {
                        'Cache-Control': 'no-cache',
                    },
                });
                // Debug: Log the response to see if documents are included
                console.log('Policies response:', response.data);
                if (response.data && response.data.length > 0) {
                    console.log('First policy documents:', response.data[0]?.documents);
                }
                return response.data;
            } catch (error: any) {
                // If 401, the axios interceptor will handle logout
                // But log for debugging
                console.error('Error fetching policies:', error.response?.status, error.response?.data);
                throw error;
            }
        },
        staleTime: 0, // Always refetch to see latest documents
        refetchOnWindowFocus: true,
        refetchOnMount: true,
        retry: false, // Don't retry on auth errors
    });

    const policies = policiesData;

    // Documents by year (includes years whose leave quota was deleted) — for Policy Documents card only
    const { data: documentsByYear = [], isLoading: isLoadingDocs } = useQuery<Array<{ year: number; documents: Array<{ id?: number; name: string; url: string; uploaded_at?: string }> }>>({
        queryKey: ['policies-documents-by-year'],
        queryFn: async () => {
            const response = await api.get('/policies/documents-by-year', { headers: { 'Cache-Control': 'no-cache' } });
            return response.data;
        },
        staleTime: 0,
        refetchOnWindowFocus: true,
        refetchOnMount: true,
    });

    // When year or policies change, pre-fill quota inputs from the policy for that year (so saved values are editable)
    useEffect(() => {
        const policyForYear = policies.find((p) => p.year === year);
        if (policyForYear) {
            setCasualQuota(policyForYear.casual_leave_quota);
            setSickQuota(policyForYear.sick_leave_quota);
            setWfhQuota(policyForYear.wfh_quota);
        } else {
            // No policy for this year yet: use defaults so admin can set custom values and save
            setCasualQuota(12);
            setSickQuota(3);
            setWfhQuota(2);
        }
    }, [year, policies]);

    // Fetch acknowledgment report using React Query
    const { data: ackReport = [], isLoading: isReportLoading } = useQuery<any[]>({
        queryKey: ['policies-report', reportYear],
        queryFn: async () => {
            if (!reportYear) return [];
            const response = await api.get(`/policies/${reportYear}/report`);
            return response.data;
        },
        enabled: !!reportYear, // Only fetch when reportYear is set
        staleTime: 2 * 60 * 1000, // 2 minutes
    });

    const fetchAckReport = (year: number) => {
        setReportYear(year);
    };

    // Save policy mutation
    const savePolicyMutation = useMutationWithToast({
        mutationFn: async (data: {
            year: number;
            casual_leave_quota: number;
            sick_leave_quota: number;
            wfh_quota: number;
        }) => {
            const response = await api.post('/policies/', {
                ...data,
                is_active: true
            });
            return response.data;
        },
        successMessage: `Policy quotas for ${year} saved.`,
        errorMessage: "Failed to save policy",
        invalidateQueries: ['policies'],
    });

    const handleSavePolicy = async (e: React.FormEvent) => {
        e.preventDefault();
        savePolicyMutation.mutate({
            year,
            casual_leave_quota: casualQuota,
            sick_leave_quota: sickQuota,
            wfh_quota: wfhQuota,
        });
    };

    // Upload document mutation
    const uploadDocumentMutation = useMutationWithToast({
        mutationFn: async (data: { files: File[]; year: number; docName?: string }) => {
            // Upload files sequentially
            for (const file of data.files) {
                const formData = new FormData();
                formData.append('file', file);

                let url = `/policies/${data.year}/document`;
                if (data.files.length === 1 && data.docName) {
                    url += `?name=${encodeURIComponent(data.docName)}`;
                }

                await api.post(url, formData, {
                    headers: {
                        'Content-Type': 'multipart/form-data',
                    },
                });
            }
            return { success: true };
        },
        successMessage: (_, variables) => `${variables.files.length} document(s) uploaded successfully`,
        errorMessage: "Failed to upload document",
        invalidateQueries: ['policies', 'policies-documents-by-year'],
        onSuccess: async () => {
            setSelectedFiles([]);
            setDocName('');
            // Force refetch policies to show the new document immediately
            // Add a small delay to ensure backend commit is complete
            await new Promise(resolve => setTimeout(resolve, 500));
            // Invalidate and refetch
            queryClient.invalidateQueries({ queryKey: ['policies'] });
            queryClient.invalidateQueries({ queryKey: ['policies-documents-by-year'] });
            await queryClient.refetchQueries({
                queryKey: ['policies'],
                type: 'active',
                exact: false
            });
        },
    });

    const handleUploadDocument = async () => {
        if (selectedFiles.length === 0) return;
        uploadDocumentMutation.mutate({
            files: selectedFiles,
            year,
            docName: selectedFiles.length === 1 ? docName : undefined,
        });
    };

    // Delete document mutation
    const     deleteDocumentMutation = useMutationWithToast({
        mutationFn: async (data: { policyYear: number; docUrl: string }) => {
            await api.delete(`/policies/${data.policyYear}/document?url=${encodeURIComponent(data.docUrl)}`);
            return { success: true };
        },
        successMessage: "Document deleted",
        errorMessage: "Failed to delete document",
        invalidateQueries: ['policies', 'policies-documents-by-year'],
    });

    const handleDeleteDocument = async (policyYear: number, docUrl: string) => {
        deleteDocumentMutation.mutate({ policyYear, docUrl });
    };

    // Delete policy mutation
    const deletePolicyMutation = useMutationWithToast({
        mutationFn: async (year: number) => {
            await api.delete(`/policies/${year}`);
            return { success: true };
        },
        successMessage: (_, year) => `Policy for ${year} deleted`,
        errorMessage: "Failed to delete policy",
        invalidateQueries: ['policies'],
    });

    const [policyToDelete, setPolicyToDelete] = useState<number | null>(null);

    const handleDeletePolicy = (year: number) => {
        setPolicyToDelete(year);
    };

    const confirmDeletePolicy = () => {
        if (policyToDelete !== null) {
            deletePolicyMutation.mutate(policyToDelete);
            setPolicyToDelete(null);
        }
    };

    // Memoized filtered report for performance
    const filteredReport = useMemo(() => {
        if (!searchQuery) return ackReport;
        const query = searchQuery.toLowerCase();
        return ackReport.filter(r =>
            r.full_name?.toLowerCase().includes(query) ||
            r.email?.toLowerCase().includes(query)
        );
    }, [ackReport, searchQuery]);

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

                        <Button type="submit" disabled={savePolicyMutation.isPending} className="w-full">
                            {savePolicyMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
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
                                disabled={uploadDocumentMutation.isPending || selectedFiles.length === 0}
                                variant="secondary"
                                className="w-full"
                            >
                                {uploadDocumentMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />}
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
                                            <TableRow key={policy.id ?? policy.year} className="group">
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
                                                            onClick={() => handleDeletePolicy(policy.year)}
                                                            disabled={deletePolicyMutation.isPending}
                                                            className="h-8 w-8 p-0 text-red-500 hover:text-red-700 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-opacity"
                                                            title="Delete leave quota (documents are kept)"
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

                    {/* Card 4: Policy Documents — includes years whose quota was deleted; Acknowledge report here */}
                    <Card>
                        <CardHeader>
                            <CardTitle>Policy Documents</CardTitle>
                            <CardDescription>Documents by year. Use the shield icon to view acknowledgment report.</CardDescription>
                        </CardHeader>
                        <CardContent>
                            {isLoadingDocs ? (
                                <div className="flex justify-center p-4"><LoadingSpinner /></div>
                            ) : documentsByYear.length === 0 ? (
                                <p className="text-center text-slate-500 py-4">No documents uploaded for any year.</p>
                            ) : (
                                <Table>
                                    <TableHeader>
                                        <TableRow>
                                            <TableHead>Year</TableHead>
                                            <TableHead>Documents</TableHead>
                                            <TableHead className="w-[80px]">Report</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {documentsByYear.map((item) => (
                                            <TableRow key={`doc-${item.year}`} className="group">
                                                <TableCell className="font-medium align-top">
                                                    {item.year}
                                                </TableCell>
                                                <TableCell className="align-top">
                                                    <div className="space-y-2">
                                                        {item.documents && item.documents.length > 0 ? (
                                                            item.documents.map((doc, idx) => (
                                                                <div key={doc.id || doc.url || idx} className="flex items-center justify-between group/doc">
                                                                    <a
                                                                        href={`/api${doc.url}`}
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
                                                                        onClick={() => handleDeleteDocument(item.year, doc.url)}
                                                                        disabled={deleteDocumentMutation.isPending}
                                                                        className="h-8 w-8 p-0 text-red-500 hover:text-red-700 hover:bg-red-50 opacity-0 group-hover/doc:opacity-100 transition-opacity"
                                                                        title="Delete document"
                                                                    >
                                                                        <Trash2 className="h-4 w-4" />
                                                                    </Button>
                                                                </div>
                                                            ))
                                                        ) : (
                                                            <span className="text-slate-400 text-xs italic">No documents</span>
                                                        )}
                                                    </div>
                                                </TableCell>
                                                <TableCell className="align-top">
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        onClick={() => fetchAckReport(item.year)}
                                                        className="h-8 w-8 p-0 text-blue-500 hover:text-blue-700 hover:bg-blue-50"
                                                        title="View Acknowledgment Report"
                                                    >
                                                        <ShieldCheck className="h-4 w-4" />
                                                    </Button>
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
                                                            const docName = documentsByYear.find(item => item.year === reportYear)?.documents?.find(d => d.url === ack.document_url)?.name || "Document";
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

            {/* Delete Policy Confirmation Dialog */}
            <ConfirmDialog
                open={policyToDelete !== null}
                onOpenChange={(open) => !open && setPolicyToDelete(null)}
                onConfirm={confirmDeletePolicy}
                title="Delete Policy"
                description={`Are you sure you want to delete the leave policy for ${policyToDelete}? Quotas will be removed from the list. Uploaded documents will be kept.`}
                confirmText="Delete"
                variant="destructive"
                isLoading={deletePolicyMutation.isPending}
            />
        </div>
    );
}
