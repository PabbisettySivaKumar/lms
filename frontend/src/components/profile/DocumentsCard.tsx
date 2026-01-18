'use client';

import { useState, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { FileIcon, Trash2, Upload, Loader2, Download } from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '@/hooks/useAuth';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function DocumentsCard() {
    const { user, refreshUser } = useAuth();
    const [isUploading, setIsUploading] = useState(false);
    const [isDeleting, setIsDeleting] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files;
        if (!files || files.length === 0) return;

        setIsUploading(true);
        const formData = new FormData();
        Array.from(files).forEach((file) => {
            formData.append('files', file);
        });

        try {
            const token = localStorage.getItem('access_token');
            const res = await fetch(`${API_URL}/users/me/documents`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
                body: formData,
            });

            if (!res.ok) {
                const errorData = await res.json();
                throw new Error(errorData.detail || 'Failed to upload documents');
            }

            toast.success("Documents uploaded successfully");
            await refreshUser();
        } catch (error: any) {
            console.error("Upload error:", error);
            toast.error(error.message || "Something went wrong");
        } finally {
            setIsUploading(false);
            if (fileInputRef.current) {
                fileInputRef.current.value = '';
            }
        }
    };

    const handleDelete = async (savedFilename: string) => {
        if (!confirm("Are you sure you want to delete this document?")) return;

        setIsDeleting(savedFilename);
        try {
            const token = localStorage.getItem('access_token');
            const res = await fetch(`${API_URL}/users/me/documents/${savedFilename}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
            });

            if (!res.ok) {
                const errorData = await res.json();
                throw new Error(errorData.detail || 'Failed to delete document');
            }

            toast.success("Document deleted successfully");
            await refreshUser();
        } catch (error: any) {
            console.error("Delete error:", error);
            toast.error(error.message || "Something went wrong");
        } finally {
            setIsDeleting(null);
        }
    };

    return (
        <Card>
            <CardHeader className="flex flex-row items-center justify-between">
                <div>
                    <CardTitle>Documents</CardTitle>
                    <CardDescription>Upload and manage your documents</CardDescription>
                </div>
                <div>
                    <input
                        type="file"
                        multiple
                        className="hidden"
                        ref={fileInputRef}
                        onChange={handleUpload}
                        accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
                    />
                    <Button
                        size="sm"
                        onClick={() => fileInputRef.current?.click()}
                        disabled={isUploading}
                    >
                        {isUploading ? (
                            <Loader2 className="h-4 w-4 animate-spin mr-2" />
                        ) : (
                            <Upload className="h-4 w-4 mr-2" />
                        )}
                        Upload
                    </Button>
                </div>
            </CardHeader>
            <CardContent>
                {!user?.documents || user.documents.length === 0 ? (
                    <div className="text-center py-8 text-slate-500 text-sm">
                        No documents uploaded yet.
                    </div>
                ) : (
                    <div className="space-y-3">
                        {user.documents.map((doc, idx) => (
                            <div key={idx} className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-900 rounded-lg border border-slate-100 dark:border-slate-800">
                                <div className="flex items-center space-x-3 overflow-hidden">
                                    <div className="bg-white p-2 rounded border shadow-sm shrink-0">
                                        <FileIcon className="h-5 w-5 text-indigo-500" />
                                    </div>
                                    <div className="min-w-0">
                                        <p className="text-sm font-medium truncate text-slate-900 dark:text-slate-100">{doc.name}</p>
                                        <p className="text-xs text-slate-500">{new Date(doc.uploaded_at).toLocaleDateString()}</p>
                                    </div>
                                </div>
                                <div className="flex items-center space-x-2 shrink-0">
                                    <Button variant="ghost" size="icon" className="h-8 w-8 text-slate-500 hover:text-slate-900" asChild>
                                        <a href={`${API_URL}${doc.url}`} target="_blank" rel="noopener noreferrer" download>
                                            <Download className="h-4 w-4" />
                                        </a>
                                    </Button>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        className="h-8 w-8 text-red-500 hover:text-red-700 hover:bg-red-50"
                                        onClick={() => handleDelete(doc.saved_filename)}
                                        disabled={isDeleting === doc.saved_filename}
                                    >
                                        {isDeleting === doc.saved_filename ? (
                                            <Loader2 className="h-4 w-4 animate-spin" />
                                        ) : (
                                            <Trash2 className="h-4 w-4" />
                                        )}
                                    </Button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
