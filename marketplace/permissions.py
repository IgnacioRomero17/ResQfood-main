# marketplace/permissions.py
from rest_framework import permissions

class IsPartner(permissions.BasePermission):
    """Permite solo a usuarios con rol=partner."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and getattr(request.user, "role", "") == "partner")
