'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { LogOut, Users, CalendarDays, UserCircle, FileText } from 'lucide-react';

import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/button';

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
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      {/* Navbar */}
      <header className="sticky top-0 z-40 w-full border-b bg-white dark:bg-slate-950 shadow-sm">
        <div className="container flex h-16 items-center justify-between px-4 sm:px-8 mx-auto">
          <div className="flex items-center gap-6">
            <div className="font-bold text-xl text-slate-900 dark:text-slate-50">
              LMS
            </div>
            {user && (
              <nav className="flex items-center gap-2">
                <Link href="/dashboard">
                  <Button variant="ghost" size="sm">
                    My Dashboard
                  </Button>
                </Link>
                <Link href="/dashboard/employee/leaves">
                  <Button variant="ghost" size="sm">
                    My Leaves
                  </Button>
                </Link>
                <Link href="/dashboard/profile">
                  <Button variant="ghost" size="sm">
                    <UserCircle className="mr-2 h-4 w-4" />
                    Profile
                  </Button>
                </Link>
                <Link href="/dashboard/employee/policies">
                  <Button variant="ghost" size="sm">
                    Company Policies
                  </Button>
                </Link>
                {['manager', 'hr', 'founder', 'admin'].includes(user.role) && (
                  <Link href="/dashboard/team">
                    <Button variant="ghost" size="sm">
                      Team Approvals
                    </Button>
                  </Link>
                )}
                {['admin', 'hr', 'founder'].includes(user.role) && (
                  <Link href="/dashboard/admin/users">
                    <Button variant="ghost" size="sm">
                      <Users className="mr-2 h-4 w-4" />
                      Employee Directory
                    </Button>
                  </Link>
                )}
                {['admin', 'hr', 'founder'].includes(user.role) && (
                  <Link href="/dashboard/admin/policies">
                    <Button variant="ghost" size="sm">
                      <FileText className="mr-2 h-4 w-4" />
                      Policy Management
                    </Button>
                  </Link>
                )}
                {['admin', 'hr', 'founder'].includes(user.role) && (
                  <Link href="/dashboard/admin/holidays">
                    <Button variant="ghost" size="sm">
                      <CalendarDays className="mr-2 h-4 w-4" />
                      Holiday Planner
                    </Button>
                  </Link>
                )}
              </nav>
            )}
          </div>

          <div className="flex items-center gap-4">
            {user ? (
              <span className="text-sm font-medium text-slate-700 dark:text-slate-200">
                {user.full_name}
              </span>
            ) : (
              // Placeholder while loading user details
              <div className="h-4 w-32 bg-slate-200 animate-pulse rounded" />
            )}
            <Button variant="outline" size="sm" onClick={logout}>
              <LogOut className="mr-2 h-4 w-4" />
              Logout
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 sm:px-8 py-8">
        {children}
      </main>
    </div>
  );
}
