'use client';

import { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Loader2, Plus, FileText, Trash2, Upload } from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';

import api from '@/lib/axios';
import { Button } from '@/components/ui/button';
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from '@/components/ui/card';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from '@/components/ui/dialog';
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

interface Policy {
    _id: string;
    title: string;
    file_url: string;
    created_at: string;
}

export default function AdminPoliciesPage() {
    const [isUploadOpen, setIsUploadOpen] = useState(false);
    const [title, setTitle] = useState('');
    const [file, setFile] = useState<File | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const queryClient = useQueryClient();

    // Fetch Policies
    const { data: policies, isLoading } = useQuery({
        queryKey: ['policies'],
        queryFn: async () => {
            const res = await api.get<Policy[]>('/policies');
            return res.data;
        },
    });

    // Upload Mutation
    const uploadMutation = useMutation({
        mutationFn: async (formData: FormData) => {
            await api.post('/policies/admin', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });
        },
        onSuccess: () => {
            toast.success('Policy uploaded successfully');
            queryClient.invalidateQueries({ queryKey: ['policies'] });
            handleClose();
        },
        onError: () => {
            toast.error('Failed to upload policy');
        },
    });

    // Delete Mutation
    const deleteMutation = useMutation({
        mutationFn: async (id: string) => {
            await api.delete(`/policies/admin/${id}`);
        },
        onSuccess: () => {
            toast.success('Policy deleted');
            queryClient.invalidateQueries({ queryKey: ['policies'] });
        },
        onError: () => {
            toast.error('Failed to delete policy');
        },
    });

    const handleClose = () => {
        setIsUploadOpen(false);
        setTitle('');
        setFile(null);
        if (fileInputRef.current) fileInputRef.current.value = '';
    };

    const handleUpload = () => {
        if (!title || !file) return;
        const formData = new FormData();
        formData.append('title', title);
        formData.append('file', file);
        uploadMutation.mutate(formData);
    };

    if (isLoading) {
        return (
            <div className="flex justify-center p-8">
                <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-50">Policy Management</h1>
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                        Upload and manage company policies and documents.
                    </p>
                </div>
                <Dialog open={isUploadOpen} onOpenChange={setIsUploadOpen}>
                    <DialogTrigger asChild>
                        <Button>
                            <Plus className="mr-2 h-4 w-4" />
                            Upload Policy
                        </Button>
                    </DialogTrigger>
                    <DialogContent>
                        <DialogHeader>
                            <DialogTitle>Upload New Policy</DialogTitle>
                            <DialogDescription>
                                Upload a PDF document for employees to review.
                            </DialogDescription>
                        </DialogHeader>
                        <div className="space-y-4 py-4">
                            <div className="space-y-2">
                                <Label htmlFor="title">Policy Title</Label>
                                <Input
                                    id="title"
                                    placeholder="e.g. Employee Handbook 2026"
                                    value={title}
                                    onChange={(e) => setTitle(e.target.value)}
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="file">PDF Document</Label>
                                <Input
                                    id="file"
                                    type="file"
                                    accept=".pdf"
                                    ref={fileInputRef}
                                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                                />
                            </div>
                        </div>
                        <DialogFooter>
                            <Button variant="outline" onClick={handleClose}>Cancel</Button>
                            <Button onClick={handleUpload} disabled={!title || !file || uploadMutation.isPending}>
                                {uploadMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                Upload
                            </Button>
                        </DialogFooter>
                    </DialogContent>
                </Dialog>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle>Existing Policies</CardTitle>
                    <CardDescription>
                        List of active policies visible to employees.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Title</TableHead>
                                <TableHead>Uploaded Date</TableHead>
                                <TableHead>File</TableHead>
                                <TableHead className="text-right">Actions</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {policies?.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={4} className="text-center py-8 text-slate-500">
                                        No policies uploaded yet.
                                    </TableCell>
                                </TableRow>
                            ) : (
                                policies?.map((policy) => (
                                    <TableRow key={policy._id}>
                                        <TableCell className="font-medium">
                                            <div className="flex items-center">
                                                <FileText className="mr-2 h-4 w-4 text-slate-500" />
                                                {policy.title}
                                            </div>
                                        </TableCell>
                                        <TableCell>
                                            {format(new Date(policy.created_at), 'PPP')}
                                        </TableCell>
                                        <TableCell>
                                            <a
                                                href={`${process.env.NEXT_PUBLIC_API_URL}${policy.file_url}`}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="text-blue-600 hover:underline text-sm"
                                            >
                                                View PDF
                                            </a>
                                        </TableCell>
                                        <TableCell className="text-right">
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                className="text-red-600 hover:text-red-700 hover:bg-red-50"
                                                onClick={() => {
                                                    if (confirm('Are you sure you want to delete this policy?')) {
                                                        deleteMutation.mutate(policy._id);
                                                    }
                                                }}
                                            >
                                                <Trash2 className="h-4 w-4" />
                                            </Button>
                                        </TableCell>
                                    </TableRow>
                                ))
                            )}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>
        </div>
    );
}
