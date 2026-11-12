"""Demo role selection. This is a presentation mechanism, not authentication."""
from rest_framework.permissions import BasePermission

VALID_ROLES = {"funcionario", "supervisor", "gerente", "administrador"}


class DemoRolePermission(BasePermission):
    def has_permission(self, request, view):
        return getattr(request, "demo_role", None) in VALID_ROLES
