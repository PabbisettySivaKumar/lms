'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
    LayoutDashboard,
    Calendar,
    User,
    FileText,
    Users,
    LogOut,
    CheckSquare,
    ChevronsUpDown,
    Sun,
    Moon,
    Laptop,
    Settings
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
    DropdownMenuSub,
    DropdownMenuSubTrigger,
    DropdownMenuSubContent,
    DropdownMenuPortal,
} from '@/components/ui/dropdown-menu';
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from "@/components/ui/tooltip"
import { useTheme } from 'next-themes';

interface SidebarProps {
    className?: string;
}

export default function Sidebar({ className }: SidebarProps) {
    const pathname = usePathname();
    const router = useRouter();
    const { user, logout } = useAuth();
    const { setTheme } = useTheme();

    if (!user) return null;

    const isActive = (path: string) => {
        return pathname === path || pathname.startsWith(`${path}/`);
    };

    const navItems = [
        {
            title: 'Home',
            href: '/dashboard',
            icon: LayoutDashboard,
            exact: true
        },
        {
            title: 'Leaves',
            href: '/dashboard/employee/leaves',
            icon: Calendar,
        },
        {
            title: 'Policies',
            href: '/dashboard/employee/policies',
            icon: FileText,
        },
    ];

    // Manager / HR Links
    const managerLinks = [
        {
            title: 'Team Approvals',
            href: '/dashboard/team',
            icon: CheckSquare,
            roles: ['manager', 'hr', 'founder', 'admin']
        }
    ];

    // Admin Links
    const adminLinks = [
        {
            title: 'Employee Directory',
            href: '/dashboard/admin/users',
            icon: Users,
            roles: ['admin', 'hr', 'founder']
        },
        {
            title: 'Policy Management',
            href: '/dashboard/admin/policies',
            icon: FileText,
            roles: ['admin', 'hr', 'founder']
        },
        {
            title: 'Holiday Planner',
            href: '/dashboard/admin/holidays',
            icon: Calendar,
            roles: ['admin', 'hr', 'founder']
        }
    ];


    return (
        <TooltipProvider>
            <div className={cn("pb-12 min-h-screen w-[70px] bg-slate-900 text-white flex flex-col z-50", className)}>
                <div className="space-y-4 py-4 flex flex-col h-full items-center">
                    <div className="py-2 flex items-center justify-center h-12 mb-2 w-full">
                        {/* Logo / Title */}
                        <div className="font-bold text-xl">LMS</div>
                    </div>

                    <div className="w-full px-2 flex-1 flex flex-col items-center gap-2">
                        {navItems.map((item) => (
                            <Tooltip key={item.href} delayDuration={0}>
                                <TooltipTrigger asChild>
                                    <Link href={item.href} className="w-full flex justify-center">
                                        <Button
                                            variant="ghost"
                                            className={cn(
                                                "h-10 w-10 p-0 rounded-md",
                                                (item.exact ? pathname === item.href : pathname.startsWith(item.href))
                                                    ? "bg-blue-600 text-white hover:bg-blue-700"
                                                    : "text-slate-300 hover:text-white hover:bg-slate-800"
                                            )}
                                        >
                                            <item.icon className="h-5 w-5" />
                                        </Button>
                                    </Link>
                                </TooltipTrigger>
                                <TooltipContent side="right">
                                    <p>{item.title}</p>
                                </TooltipContent>
                            </Tooltip>
                        ))}

                        {/* Separator if needed */}
                        <div className="h-px w-8 bg-slate-700 my-2" />

                        {managerLinks.map((item) => {
                            if (!item.roles.includes(user.role)) return null;
                            return (
                                <Tooltip key={item.href} delayDuration={0}>
                                    <TooltipTrigger asChild>
                                        <Link href={item.href} className="w-full flex justify-center">
                                            <Button
                                                variant="ghost"
                                                className={cn(
                                                    "h-10 w-10 p-0 rounded-md",
                                                    isActive(item.href) ? "bg-blue-600 text-white hover:bg-blue-700" : "text-slate-300 hover:text-white hover:bg-slate-800"
                                                )}
                                            >
                                                <item.icon className="h-5 w-5" />
                                            </Button>
                                        </Link>
                                    </TooltipTrigger>
                                    <TooltipContent side="right">
                                        <p>{item.title}</p>
                                    </TooltipContent>
                                </Tooltip>
                            );
                        })}
                        {adminLinks.map((item) => {
                            if (!item.roles.includes(user.role)) return null;
                            return (
                                <Tooltip key={item.href} delayDuration={0}>
                                    <TooltipTrigger asChild>
                                        <Link href={item.href} className="w-full flex justify-center">
                                            <Button
                                                variant="ghost"
                                                className={cn(
                                                    "h-10 w-10 p-0 rounded-md",
                                                    isActive(item.href) ? "bg-blue-600 text-white hover:bg-blue-700" : "text-slate-300 hover:text-white hover:bg-slate-800"
                                                )}
                                            >
                                                <item.icon className="h-5 w-5" />
                                            </Button>
                                        </Link>
                                    </TooltipTrigger>
                                    <TooltipContent side="right">
                                        <p>{item.title}</p>
                                    </TooltipContent>
                                </Tooltip>
                            );
                        })}
                    </div>

                    <div className="px-2 pb-4 mt-auto w-full flex flex-col items-center gap-4">
                        <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                                <Button variant="ghost" className="h-10 w-10 p-0 rounded-full hover:bg-slate-800 ring-2 ring-transparent hover:ring-slate-600">
                                    <Avatar className="h-8 w-8 border border-slate-600">
                                        <AvatarImage src="" />
                                        <AvatarFallback className="bg-slate-700 text-slate-200 text-xs">
                                            {user.full_name?.charAt(0) || 'U'}
                                        </AvatarFallback>
                                    </Avatar>
                                </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent className="w-56" align="start" side="right" sideOffset={10} forceMount>
                                <DropdownMenuLabel>
                                    <div className="flex flex-col">
                                        <span>{user.full_name}</span>
                                        <span className="text-xs font-normal text-slate-500 capitalize">{user.role}</span>
                                    </div>
                                </DropdownMenuLabel>
                                <DropdownMenuSeparator />
                                <DropdownMenuItem onClick={() => router.push('/dashboard/profile')}>
                                    <User className="mr-2 h-4 w-4" />
                                    Profile
                                </DropdownMenuItem>
                                <DropdownMenuItem onClick={() => router.push('/dashboard/settings')}>
                                    <Settings className="mr-2 h-4 w-4" />
                                    Settings
                                </DropdownMenuItem>
                                <DropdownMenuSub>
                                    <DropdownMenuSubTrigger>
                                        <Sun className="mr-2 h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
                                        <Moon className="absolute mr-2 h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
                                        <span className="ml-2">Theme</span>
                                    </DropdownMenuSubTrigger>
                                    <DropdownMenuPortal>
                                        <DropdownMenuSubContent>
                                            <DropdownMenuItem onClick={() => setTheme("light")}>
                                                <Sun className="mr-2 h-4 w-4" />
                                                Light
                                            </DropdownMenuItem>
                                            <DropdownMenuItem onClick={() => setTheme("dark")}>
                                                <Moon className="mr-2 h-4 w-4" />
                                                Dark
                                            </DropdownMenuItem>
                                            <DropdownMenuItem onClick={() => setTheme("system")}>
                                                <Laptop className="mr-2 h-4 w-4" />
                                                System
                                            </DropdownMenuItem>
                                        </DropdownMenuSubContent>
                                    </DropdownMenuPortal>
                                </DropdownMenuSub>
                            </DropdownMenuContent>
                        </DropdownMenu>

                        <Tooltip delayDuration={0}>
                            <TooltipTrigger asChild>
                                <Button
                                    variant="ghost"
                                    onClick={logout}
                                    className="h-10 w-10 p-0 rounded-md text-red-400 hover:text-red-500 hover:bg-slate-800"
                                >
                                    <LogOut className="h-5 w-5" />
                                </Button>
                            </TooltipTrigger>
                            <TooltipContent side="right">
                                <p>Log out</p>
                            </TooltipContent>
                        </Tooltip>
                    </div>
                </div>
            </div>
        </TooltipProvider>
    );
}
