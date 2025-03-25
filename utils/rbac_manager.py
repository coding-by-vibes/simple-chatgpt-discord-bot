from enum import Enum
from typing import Dict, List, Optional, Set
import json
import os
from datetime import datetime
import logging

class Permission(Enum):
    # User Management
    MANAGE_USERS = "manage_users"
    VIEW_USERS = "view_users"
    
    # Content Management
    MANAGE_CONTENT = "manage_content"
    VIEW_CONTENT = "view_content"
    
    # Analytics
    VIEW_ANALYTICS = "view_analytics"
    MANAGE_ANALYTICS = "manage_analytics"
    
    # Settings
    MANAGE_SETTINGS = "manage_settings"
    VIEW_SETTINGS = "view_settings"
    
    # Personas
    MANAGE_PERSONAS = "manage_personas"
    VIEW_PERSONAS = "view_personas"
    
    # Rate Limits
    MANAGE_RATE_LIMITS = "manage_rate_limits"
    VIEW_RATE_LIMITS = "view_rate_limits"
    
    # Security
    MANAGE_SECURITY = "manage_security"
    VIEW_SECURITY = "view_security"

class Role(Enum):
    ADMIN = "admin"
    MODERATOR = "moderator"
    USER = "user"
    GUEST = "guest"

class RBACManager:
    def __init__(self, settings_dir: str):
        """Initialize the RBAC manager.
        
        Args:
            settings_dir: Directory to store RBAC data
        """
        self.settings_dir = settings_dir
        self.rbac_dir = os.path.join(settings_dir, "rbac")
        self.logger = logging.getLogger(__name__)
        
        # Create RBAC directory
        os.makedirs(self.rbac_dir, exist_ok=True)
        
        # Initialize default role permissions
        self.default_role_permissions = {
            Role.ADMIN.value: {p.value for p in Permission},  # All permissions
            Role.MODERATOR.value: {
                Permission.VIEW_USERS.value,
                Permission.VIEW_CONTENT.value,
                Permission.MANAGE_CONTENT.value,
                Permission.VIEW_ANALYTICS.value,
                Permission.VIEW_SETTINGS.value,
                Permission.VIEW_PERSONAS.value,
                Permission.VIEW_RATE_LIMITS.value,
                Permission.VIEW_SECURITY.value
            },
            Role.USER.value: {
                Permission.VIEW_CONTENT.value,
                Permission.VIEW_PERSONAS.value
            },
            Role.GUEST.value: {
                Permission.VIEW_CONTENT.value
            }
        }
        
        # Load or create role permissions
        self.role_permissions = self._load_role_permissions()
        
    def _get_role_file_path(self) -> str:
        """Get the path to the role permissions file."""
        return os.path.join(self.rbac_dir, "role_permissions.json")
    
    def _load_role_permissions(self) -> Dict[str, Set[str]]:
        """Load role permissions from file or create default."""
        file_path = self._get_role_file_path()
        
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    # Convert lists to sets
                    return {role: set(perms) for role, perms in data.items()}
            except Exception as e:
                self.logger.error(f"Error loading role permissions: {e}")
                return self.default_role_permissions
        
        # If file doesn't exist, use defaults and save them
        self._save_role_permissions(self.default_role_permissions)
        return self.default_role_permissions
    
    def _save_role_permissions(self, permissions: Dict[str, Set[str]]) -> None:
        """Save role permissions to file."""
        try:
            # Convert sets to lists for JSON serialization
            data = {role: list(perms) for role, perms in permissions.items()}
            
            with open(self._get_role_file_path(), 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            self.logger.error(f"Error saving role permissions: {e}")
    
    def get_role_permissions(self, role: str) -> Set[str]:
        """Get permissions for a specific role."""
        return self.role_permissions.get(role, set())
    
    def has_permission(self, user_id: str, permission: Permission) -> bool:
        """Check if a user has a specific permission."""
        user_role = self.get_user_role(user_id)
        if not user_role:
            return False
        
        return permission.value in self.get_role_permissions(user_role)
    
    def get_user_role(self, user_id: str) -> Optional[str]:
        """Get the role of a specific user."""
        try:
            file_path = os.path.join(self.rbac_dir, "user_roles.json")
            if not os.path.exists(file_path):
                return Role.GUEST.value
            
            with open(file_path, 'r') as f:
                user_roles = json.load(f)
                return user_roles.get(user_id, Role.GUEST.value)
        except Exception as e:
            self.logger.error(f"Error getting user role: {e}")
            return Role.GUEST.value
    
    def set_user_role(self, user_id: str, role: str) -> bool:
        """Set the role for a specific user."""
        try:
            if role not in [r.value for r in Role]:
                return False
            
            file_path = os.path.join(self.rbac_dir, "user_roles.json")
            
            # Load existing roles
            user_roles = {}
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    user_roles = json.load(f)
            
            # Update role
            user_roles[user_id] = role
            
            # Save updated roles
            with open(file_path, 'w') as f:
                json.dump(user_roles, f, indent=4)
            
            return True
        except Exception as e:
            self.logger.error(f"Error setting user role: {e}")
            return False
    
    def add_role_permission(self, role: str, permission: Permission) -> bool:
        """Add a permission to a role."""
        try:
            if role not in self.role_permissions:
                return False
            
            self.role_permissions[role].add(permission.value)
            self._save_role_permissions(self.role_permissions)
            return True
        except Exception as e:
            self.logger.error(f"Error adding role permission: {e}")
            return False
    
    def remove_role_permission(self, role: str, permission: Permission) -> bool:
        """Remove a permission from a role."""
        try:
            if role not in self.role_permissions:
                return False
            
            self.role_permissions[role].discard(permission.value)
            self._save_role_permissions(self.role_permissions)
            return True
        except Exception as e:
            self.logger.error(f"Error removing role permission: {e}")
            return False
    
    def get_user_permissions(self, user_id: str) -> Set[str]:
        """Get all permissions for a user based on their role."""
        role = self.get_user_role(user_id)
        return self.get_role_permissions(role)
    
    def reset_role_permissions(self) -> bool:
        """Reset all role permissions to default."""
        try:
            self.role_permissions = self.default_role_permissions.copy()
            self._save_role_permissions(self.role_permissions)
            return True
        except Exception as e:
            self.logger.error(f"Error resetting role permissions: {e}")
            return False 