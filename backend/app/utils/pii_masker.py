"""
PII Masking Utilities
"""
import re
from typing import Any, Dict


def mask_email(email: str) -> str:
    """Mask email address"""
    if not email or "@" not in email:
        return email
    
    parts = email.split("@")
    if len(parts) != 2:
        return email
    
    username = parts[0]
    domain = parts[1]
    
    if len(username) <= 2:
        masked_username = "*" * len(username)
    else:
        masked_username = username[0] + "*" * (len(username) - 2) + username[-1]
    
    return f"{masked_username}@{domain}"


def mask_phone(phone: str) -> str:
    """Mask phone number"""
    if not phone:
        return phone
    
    # Remove non-digits
    digits = re.sub(r'\D', '', phone)
    
    if len(digits) < 4:
        return "*" * len(phone)
    
    # Show first 2 and last 2 digits
    return phone[:2] + "*" * (len(phone) - 4) + phone[-2:]


def mask_name(name: str) -> str:
    """Mask name (show first letter only)"""
    if not name:
        return name
    
    if len(name) <= 1:
        return "*"
    
    return name[0] + "*" * (len(name) - 1)


def redact_pii(data: Any) -> Any:
    """
    Redact PII from data structure
    Recursively processes dicts, lists, and strings
    """
    if isinstance(data, dict):
        redacted = {}
        for key, value in data.items():
            key_lower = str(key).lower()
            
            # Check for PII fields
            if any(pii in key_lower for pii in ['email', 'mail']):
                redacted[key] = mask_email(str(value)) if value else value
            elif any(pii in key_lower for pii in ['phone', 'tel', 'mobile']):
                redacted[key] = mask_phone(str(value)) if value else value
            elif any(pii in key_lower for pii in ['name', 'firstname', 'lastname', 'fullname']):
                redacted[key] = mask_name(str(value)) if value else value
            else:
                redacted[key] = redact_pii(value)
        
        return redacted
    
    elif isinstance(data, list):
        return [redact_pii(item) for item in data]
    
    elif isinstance(data, str):
        # Check if string contains email or phone
        if "@" in data and "." in data:
            return mask_email(data)
        elif re.search(r'\d{10,}', data):
            return mask_phone(data)
        else:
            return data
    
    else:
        return data
