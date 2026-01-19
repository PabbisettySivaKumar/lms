'use client';

import { useState } from 'react';
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
    ChevronLeft,
    ChevronRight,
    Sun,
    Moon,
    Laptop,
    Settings,
    FileSpreadsheet
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
    const [isExpanded, setIsExpanded] = useState(false);

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
        },
        {
            title: 'Leave Reports',
            href: '/dashboard/admin/export',
            icon: FileSpreadsheet,
            roles: ['admin', 'hr', 'founder']
        }
    ];


    return (
        <TooltipProvider>
            <div
                className={cn(
                    "pb-12 min-h-screen bg-slate-900 text-white flex flex-col z-50 transition-all duration-300 ease-in-out",
                    isExpanded ? "w-64" : "w-[70px]",
                    className
                )}
            >
                <div className="space-y-4 py-4 flex flex-col h-full">
                    <div className={cn("py-2 flex items-center h-12 mb-2 w-full px-4", isExpanded ? "justify-between" : "justify-center")}>
                        {/* Logo / Title */}
                        <div className={cn("font-bold text-xl transition-all duration-300", isExpanded ? "opacity-100" : "opacity-100")}>
                            {isExpanded ? "Leave Management" : "LMS"}
                        </div>
                    </div>

                    <div className="w-full px-2 flex-1 flex flex-col gap-2">
                        {navItems.map((item) => {
                            const btn = (
                                <Link href={item.href} className="w-full">
                                    <Button
                                        variant="ghost"
                                        className={cn(
                                            "w-full rounded-md transition-all duration-200",
                                            isExpanded ? "justify-start px-3" : "justify-center px-0 w-10 mx-auto",
                                            (item.exact ? pathname === item.href : pathname.startsWith(item.href))
                                                ? "bg-blue-600 text-white hover:bg-blue-700"
                                                : "text-slate-300 hover:text-white hover:bg-slate-800"
                                        )}
                                    >
                                        <item.icon className={cn("h-5 w-5", isExpanded && "mr-3")} />
                                        {isExpanded && <span className="truncate">{item.title}</span>}
                                    </Button>
                                </Link>
                            );

                            if (isExpanded) return <div key={item.href} className="w-full">{btn}</div>;

                            return (
                                <Tooltip key={item.href} delayDuration={0}>
                                    <TooltipTrigger asChild>
                                        {btn}
                                    </TooltipTrigger>
                                    <TooltipContent side="right">
                                        <p>{item.title}</p>
                                    </TooltipContent>
                                </Tooltip>
                            );
                        })}

                        <div className="h-px w-full bg-slate-700 my-2 opacity-50" />

                        {managerLinks.map((item) => {
                            if (!item.roles.includes(user.role)) return null;
                            const btn = (
                                <Link href={item.href} className="w-full">
                                    <Button
                                        variant="ghost"
                                        className={cn(
                                            "w-full rounded-md transition-all duration-200",
                                            isExpanded ? "justify-start px-3" : "justify-center px-0 w-10 mx-auto",
                                            isActive(item.href) ? "bg-blue-600 text-white hover:bg-blue-700" : "text-slate-300 hover:text-white hover:bg-slate-800"
                                        )}
                                    >
                                        <item.icon className={cn("h-5 w-5", isExpanded && "mr-3")} />
                                        {isExpanded && <span className="truncate">{item.title}</span>}
                                    </Button>
                                </Link>
                            );

                            if (isExpanded) return <div key={item.href} className="w-full">{btn}</div>;

                            return (
                                <Tooltip key={item.href} delayDuration={0}>
                                    <TooltipTrigger asChild>
                                        {btn}
                                    </TooltipTrigger>
                                    <TooltipContent side="right">
                                        <p>{item.title}</p>
                                    </TooltipContent>
                                </Tooltip>
                            );
                        })}

                        {adminLinks.map((item) => {
                            if (!item.roles.includes(user.role)) return null;
                            const btn = (
                                <Link href={item.href} className="w-full">
                                    <Button
                                        variant="ghost"
                                        className={cn(
                                            "w-full rounded-md transition-all duration-200",
                                            isExpanded ? "justify-start px-3" : "justify-center px-0 w-10 mx-auto",
                                            isActive(item.href) ? "bg-blue-600 text-white hover:bg-blue-700" : "text-slate-300 hover:text-white hover:bg-slate-800"
                                        )}
                                    >
                                        <item.icon className={cn("h-5 w-5", isExpanded && "mr-3")} />
                                        {isExpanded && <span className="truncate">{item.title}</span>}
                                    </Button>
                                </Link>
                            );

                            if (isExpanded) return <div key={item.href} className="w-full">{btn}</div>;

                            return (
                                <Tooltip key={item.href} delayDuration={0}>
                                    <TooltipTrigger asChild>
                                        {btn}
                                    </TooltipTrigger>
                                    <TooltipContent side="right">
                                        <p>{item.title}</p>
                                    </TooltipContent>
                                </Tooltip>
                            );
                        })}
                    </div>

                    <div className="px-2 pb-4 mt-auto w-full flex flex-col gap-2">
                        {/* Collapse Toggle */}
                        <Button
                            variant="ghost"
                            onClick={() => setIsExpanded(!isExpanded)}
                            className={cn(
                                "text-slate-400 hover:text-white hover:bg-slate-800 mb-2",
                                isExpanded ? "w-full justify-start px-3" : "w-10 p-0 mx-auto"
                            )}
                        >
                            {isExpanded ? <ChevronLeft className="h-5 w-5 mr-3" /> : <ChevronRight className="h-5 w-5" />}
                            {isExpanded && <span>Collapse</span>}
                        </Button>

                        <div className={cn("flex items-center", isExpanded ? "justify-between px-2 bg-slate-800/50 rounded-lg p-2" : "flex-col gap-4")}>
                            <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                    <Button variant="ghost" className="h-10 w-10 p-0 rounded-full hover:bg-slate-800 ring-2 ring-transparent hover:ring-slate-600 shrink-0">
                                        <Avatar className="h-8 w-8 border border-slate-600">
                                            <AvatarImage src="" />
                                            <AvatarFallback className="bg-slate-700 text-slate-200 text-xs">
                                                {user.full_name?.charAt(0) || 'U'}
                                            </AvatarFallback>
                                        </Avatar>
                                    </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent className="w-56" align={isExpanded ? "end" : "start"} side="right" sideOffset={10} forceMount>
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

                            {isExpanded && (
                                <div className="flex flex-col overflow-hidden">
                                    <span className="text-sm font-medium truncate">{user.full_name?.split(' ')[0]}</span>
                                    <span className="text-xs text-slate-400 truncate capitalize">{user.role}</span>
                                </div>
                            )}

                            {isExpanded ? (
                                <Button
                                    variant="ghost"
                                    onClick={logout}
                                    className="w-full rounded-md text-red-400 hover:text-red-500 hover:bg-slate-900/50 justify-start px-3 transition-all duration-200"
                                >
                                    <LogOut className="h-5 w-5 mr-3" />
                                    <span className="truncate">Log out</span>
                                </Button>
                            ) : (
                                <Tooltip delayDuration={0}>
                                    <TooltipTrigger asChild>
                                        <Button
                                            variant="ghost"
                                            onClick={logout}
                                            className="h-9 w-9 p-0 rounded-md text-red-400 hover:text-red-500 hover:bg-slate-800 shrink-0"
                                        >
                                            <LogOut className="h-4 w-4" />
                                        </Button>
                                    </TooltipTrigger>
                                    <TooltipContent side="right">
                                        <p>Log out</p>
                                    </TooltipContent>
                                </Tooltip>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </TooltipProvider>
    );
}
