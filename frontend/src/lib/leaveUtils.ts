/**
 * Utility functions for leave type formatting
 */

export function formatLeaveType(leaveType: string): string {
    const leaveTypeMap: Record<string, string> = {
        'CASUAL': 'Casual/Earned Leave',
        'SICK': 'Sick Leave',
        'EARNED': 'Casual/Earned Leave', // For backward compatibility with existing EARNED leaves
        'WFH': 'Work From Home',
        'COMP_OFF': 'Comp-Off',
        'MATERNITY': 'Maternity Leave',
        'SABBATICAL': 'Sabbatical Leave',
    };
    
    return leaveTypeMap[leaveType] || leaveType.replace('_', ' ');
}
