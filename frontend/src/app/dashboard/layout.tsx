'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { LogOut, Users, CalendarDays, UserCircle, FileText } from 'lucide-react';

import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/button';
import Sidebar from '@/components/layout/Sidebar';
import { ErrorBoundary } from '@/components/common/ErrorBoundary';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, logout, fetchUser, isLoading } = useAuth();
  const router = useRouter();
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
    fetchUser();
  }, []);

  // Simple protection sync
  useEffect(() => {
    if (isMounted && !isLoading && !user && !localStorage.getItem('access_token')) {
      router.push('/login');
    }
  }, [user, isLoading, router, isMounted]);

  // Prevent hydration mismatch or flash by not rendering until mounted
  if (!isMounted) return null;

  return (
    <ErrorBoundary>
      <div className="flex h-screen overflow-hidden bg-slate-50 dark:bg-slate-900">
        {/* Sidebar - Hidden on mobile, usually? For now just show it. */}
        {user && <Sidebar className="shrink-0" />}

        {/* Main Content */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          <main className="flex-1 overflow-y-auto p-4 sm:p-8">
            {children}
          </main>
        </div>
      </div>
    </ErrorBoundary>
  );
}
