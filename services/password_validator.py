"""
Password validation service — enforces password complexity policy.
"""
import re


def validate_password(password: str) -> tuple:
    """
    Enforce password policy.
    Returns (is_valid: bool, error_message: str).
    """
    if len(password) < 8:
        return False, 'Password must be at least 8 characters.'
    if not re.search(r'[A-Z]', password):
        return False, 'Password must contain at least one uppercase letter.'
    if not re.search(r'[a-z]', password):
        return False, 'Password must contain at least one lowercase letter.'
    if not re.search(r'[0-9]', password):
        return False, 'Password must contain at least one digit.'
    return True, ''
