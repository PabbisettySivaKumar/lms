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
import { Loader2, Save, Upload, FileText } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

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

    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [docName, setDocName] = useState<string>('');

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
        if (!selectedFile) {
            toast.error("Please select a file first");
            return;
        }

        setIsUploading(true);
        try {
            const token = localStorage.getItem('access_token');
            const formData = new FormData();
            formData.append('file', selectedFile);

            const url = new URL(`${API_URL}/policies/${year}/document`);
            if (docName) url.searchParams.append('name', docName);

            const res = await fetch(url.toString(), {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                },
                body: formData
            });

            if (!res.ok) {
                // Determine if 404 (policy mismatch) logic handled in backend
                if (res.status === 404) {
                    throw new Error(`Policy for ${year} not found. Save quotas first.`);
                }
                throw new Error("Upload failed");
            }

            toast.success("Document uploaded successfully");
            await fetchPolicies();
            setSelectedFile(null);
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
                                    onChange={(e) => setSelectedFile(e.target.files ? e.target.files[0] : null)}
                                />
                                {selectedFile && (
                                    <p className="text-xs text-blue-600">Selected: {selectedFile.name}</p>
                                )}
                            </div>
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
                            <Button
                                onClick={handleUploadDocument}
                                disabled={isUploading || !selectedFile}
                                variant="secondary"
                                className="w-full"
                            >
                                {isUploading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />}
                                Upload Document
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
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {policies.map((policy) => (
                                            <TableRow key={policy._id}>
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
                                                                        className="h-6 px-2 text-red-500 hover:text-red-700 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-opacity"
                                                                    >
                                                                        Delete
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
        </div>
    );
}
