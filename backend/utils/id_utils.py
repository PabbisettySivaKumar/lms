"""
ID conversion utilities for MySQL
"""
from typing import Union, Optional


def to_int_id(id_value: Union[str, int, None]) -> Optional[int]:
    """
    Convert ID to integer.
    Handles both string and integer IDs.
    
    Args:
        id_value: ID as string, int, or None
        
    Returns:
        Integer ID or None
    """
    if id_value is None:
        return None
    
    if isinstance(id_value, int):
        return id_value
    
    if isinstance(id_value, str):
        try:
            return int(id_value)
        except ValueError:
            return None
    
    return None


def is_valid_id(id_value: Union[str, int, None]) -> bool:
    """
    Check if ID is valid (can be converted to int).
    
    Args:
        id_value: ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    return to_int_id(id_value) is not None
