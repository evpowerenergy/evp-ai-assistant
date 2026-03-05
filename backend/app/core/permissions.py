"""
Permission Checking and RBAC
"""
from typing import Dict, Any, List
from app.utils.logger import get_logger
from app.services.supabase import get_supabase_client

logger = get_logger(__name__)


# Role hierarchy (higher number = more permissions)
ROLE_HIERARCHY = {
    "admin": 3,
    "manager": 2,
    "staff": 1,
    "system": 0
}

# Resource permissions mapping
RESOURCE_PERMISSIONS = {
    "chat": {
        "read": ["admin", "manager", "staff"],
        "write": ["admin", "manager", "staff"]
    },
    "documents": {
        "read": ["admin", "manager", "staff"],
        "write": ["admin"],
        "delete": ["admin"]
    },
    "audit_logs": {
        "read": ["admin", "manager"],
        "write": ["system"]  # Only system can write audit logs
    },
    "line": {
        "read": ["admin", "manager", "staff"],
        "write": ["admin", "manager", "staff"],
        "link": ["admin"]
    }
}


def has_permission(user_role: str, required_role: str) -> bool:
    """
    Check if user has required role or higher
    """
    user_level = ROLE_HIERARCHY.get(user_role, 0)
    required_level = ROLE_HIERARCHY.get(required_role, 0)
    
    return user_level >= required_level


def can_access_resource(
    user: Dict[str, Any],
    resource_type: str,
    action: str = "read",
    resource_id: str = None
) -> bool:
    """
    Check if user can access a specific resource
    This will be expanded based on RLS policies
    """
    user_role = user.get("role", "staff")
    user_id = user.get("id")
    
    # Check resource permissions
    resource_perms = RESOURCE_PERMISSIONS.get(resource_type, {})
    allowed_roles = resource_perms.get(action, [])
    
    if user_role in allowed_roles:
        return True
    
    # Admin can access everything
    if user_role == "admin":
        return True
    
    # Manager can access team resources
    if user_role == "manager":
        # TODO: Implement team-based access check
        # For now, allow if action is in allowed roles
        return action in resource_perms.get("read", [])
    
    # Staff can only access their own resources
    if user_role == "staff":
        # Check if resource belongs to user
        if resource_type == "chat" and resource_id:
            # Will be checked via RLS
            return True
        return action in resource_perms.get("read", [])
    
    return False


async def check_resource_permission(
    user: Dict[str, Any],
    resource_type: str,
    action: str = "read",
    resource_id: str = None
) -> bool:
    """
    Async version of can_access_resource
    Can query database if needed
    """
    # Basic permission check
    if not can_access_resource(user, resource_type, action, resource_id):
        return False
    
    # Additional database-level checks
    if resource_type == "chat" and resource_id:
        # Check if session belongs to user
        try:
            supabase = get_supabase_client()
            result = supabase.table("chat_sessions").select("user_id").eq("id", resource_id).single().execute()
            
            if result.data:
                session_user_id = result.data.get("user_id")
                return session_user_id == user.get("id")
        except Exception as e:
            logger.error(f"Error checking resource permission: {e}")
            return False
    
    return True


def filter_by_role(data: Any, user_role: str) -> Any:
    """
    Filter data based on user role
    Removes sensitive fields for lower roles
    """
    if not isinstance(data, dict):
        return data
    
    filtered = data.copy()
    
    # Remove sensitive fields for non-admin users
    if user_role != "admin":
        sensitive_fields = [
            "service_role_key",
            "api_key",
            "secret",
            "password",
            "token"
        ]
        
        for field in sensitive_fields:
            filtered.pop(field, None)
    
    return filtered
