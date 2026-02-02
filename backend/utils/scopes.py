"""
OAuth2 Scope definitions and role-to-scope mapping.
Provides fine-grained permission control based on OAuth2 standards.
"""
from typing import List
from backend.models.user import UserRole


class Scope:
    """Available OAuth2 scopes for the application."""
    
    # Leave scopes
    READ_LEAVES = "read:leaves"
    WRITE_LEAVES = "write:leaves"
    APPROVE_LEAVES = "approve:leaves"
    CANCEL_LEAVES = "cancel:leaves"
    
    # User scopes
    READ_USERS = "read:users"
    WRITE_USERS = "write:users"
    ADMIN_USERS = "admin:users"
    
    # Holiday scopes
    READ_HOLIDAYS = "read:holidays"
    WRITE_HOLIDAYS = "write:holidays"
    
    # Policy scopes
    READ_POLICIES = "read:policies"
    WRITE_POLICIES = "write:policies"
    ACKNOWLEDGE_POLICIES = "acknowledge:policies"
    
    # System scopes
    ADMIN_SYSTEM = "admin:system"
    TRIGGER_JOBS = "trigger:jobs"
    EXPORT_DATA = "export:data"


# Map roles to their default scopes
ROLE_SCOPES = {
    UserRole.EMPLOYEE: [
        Scope.READ_LEAVES,
        Scope.WRITE_LEAVES,
        Scope.CANCEL_LEAVES,
        Scope.READ_HOLIDAYS,
        Scope.READ_POLICIES,
        Scope.ACKNOWLEDGE_POLICIES,
    ],
    UserRole.MANAGER: [
        Scope.READ_LEAVES,
        Scope.WRITE_LEAVES,
        Scope.APPROVE_LEAVES,
        Scope.CANCEL_LEAVES,
        Scope.READ_USERS,
        Scope.READ_HOLIDAYS,
        Scope.READ_POLICIES,
        Scope.ACKNOWLEDGE_POLICIES,
    ],
    UserRole.HR: [
        Scope.READ_LEAVES,
        Scope.WRITE_LEAVES,
        Scope.APPROVE_LEAVES,
        Scope.CANCEL_LEAVES,
        Scope.READ_USERS,
        Scope.WRITE_USERS,
        Scope.ADMIN_USERS,  # HR can add/manage employees
        Scope.READ_HOLIDAYS,
        Scope.WRITE_HOLIDAYS,
        Scope.READ_POLICIES,
        Scope.WRITE_POLICIES,
        Scope.ACKNOWLEDGE_POLICIES,
        Scope.EXPORT_DATA,  # HR can export leave reports
    ],
    UserRole.ADMIN: [
        Scope.READ_LEAVES,
        Scope.WRITE_LEAVES,
        Scope.APPROVE_LEAVES,
        Scope.CANCEL_LEAVES,
        Scope.READ_USERS,
        Scope.WRITE_USERS,
        Scope.ADMIN_USERS,
        Scope.READ_HOLIDAYS,
        Scope.WRITE_HOLIDAYS,
        Scope.READ_POLICIES,
        Scope.WRITE_POLICIES,
        Scope.ACKNOWLEDGE_POLICIES,
        Scope.ADMIN_SYSTEM,
        Scope.TRIGGER_JOBS,
        Scope.EXPORT_DATA,
    ],
    UserRole.FOUNDER: [
        # Founder has all scopes (same as ADMIN)
        Scope.READ_LEAVES,
        Scope.WRITE_LEAVES,
        Scope.APPROVE_LEAVES,
        Scope.CANCEL_LEAVES,
        Scope.READ_USERS,
        Scope.WRITE_USERS,
        Scope.ADMIN_USERS,
        Scope.READ_HOLIDAYS,
        Scope.WRITE_HOLIDAYS,
        Scope.READ_POLICIES,
        Scope.WRITE_POLICIES,
        Scope.ACKNOWLEDGE_POLICIES,
        Scope.ADMIN_SYSTEM,
        Scope.TRIGGER_JOBS,
        Scope.EXPORT_DATA,
    ],
    UserRole.CO_FOUNDER: [
        # Co-founder has same scopes as Founder
        Scope.READ_LEAVES,
        Scope.WRITE_LEAVES,
        Scope.APPROVE_LEAVES,
        Scope.CANCEL_LEAVES,
        Scope.READ_USERS,
        Scope.WRITE_USERS,
        Scope.ADMIN_USERS,
        Scope.READ_HOLIDAYS,
        Scope.WRITE_HOLIDAYS,
        Scope.READ_POLICIES,
        Scope.WRITE_POLICIES,
        Scope.ACKNOWLEDGE_POLICIES,
        Scope.ADMIN_SYSTEM,
        Scope.TRIGGER_JOBS,
        Scope.EXPORT_DATA,
    ],
    UserRole.INTERN: [
        Scope.READ_LEAVES,
        Scope.WRITE_LEAVES,
        Scope.CANCEL_LEAVES,
        Scope.READ_HOLIDAYS,
        Scope.READ_POLICIES,
        Scope.ACKNOWLEDGE_POLICIES,
    ],
    UserRole.CONTRACT: [
        Scope.READ_LEAVES,
        Scope.WRITE_LEAVES,
        Scope.CANCEL_LEAVES,
        Scope.READ_HOLIDAYS,
        Scope.READ_POLICIES,
        Scope.ACKNOWLEDGE_POLICIES,
    ],
}


def get_scopes_for_role(role: UserRole) -> List[str]:
    """
    Get default scopes for a given role.
    
    Args:
        role: UserRole enum value
        
    Returns:
        List of scope strings for the role
    """
    return ROLE_SCOPES.get(role, [])


def has_scope(token_scopes: List[str], required_scope: str) -> bool:
    """
    Check if token has required scope.
    
    Args:
        token_scopes: List of scopes from JWT token
        required_scope: Required scope to check
        
    Returns:
        True if scope is present, False otherwise
    """
    return required_scope in token_scopes


def has_any_scope(token_scopes: List[str], required_scopes: List[str]) -> bool:
    """
    Check if token has any of the required scopes.
    
    Args:
        token_scopes: List of scopes from JWT token
        required_scopes: List of scopes to check (OR condition)
        
    Returns:
        True if any scope is present, False otherwise
    """
    return any(scope in token_scopes for scope in required_scopes)


def has_all_scopes(token_scopes: List[str], required_scopes: List[str]) -> bool:
    """
    Check if token has all required scopes.
    
    Args:
        token_scopes: List of scopes from JWT token
        required_scopes: List of scopes to check (AND condition)
        
    Returns:
        True if all scopes are present, False otherwise
    """
    return all(scope in token_scopes for scope in required_scopes)
