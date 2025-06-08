# permissions.py
from rest_framework import permissions
from space.models import SpaceMembership

class PostPermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False

        # Allow GET requests for authenticated users with space membership
        if request.method == "GET":
            space_id = view.kwargs.get('space_id') or (hasattr(view, 'get_object') and str(view.get_object().space.space_id))
            if space_id:
                return SpaceMembership.objects.filter(user=user, space__space_id=space_id).exists()
            return True  # Allow if no specific space_id is required

        if request.method == "POST":
            status = request.data.get('status', 'draft')
            return status == 'draft'

        if request.method in ["PUT", "PATCH", "DELETE"]:
            return True  # Defer to object-level permission check

        return False

    def has_object_permission(self, request, view, obj):
        if request.method in ["PUT", "PATCH", "DELETE"]:
            # Allow owners, superusers, or space members to update/delete
            return (obj.user == request.user or
                    request.user.is_superuser or
                    SpaceMembership.objects.filter(user=request.user, space=obj.space).exists())
        return True