import logging
from rest_framework import permissions
from .models import SpaceMembership

logger = logging.getLogger(__name__)

class IsSpaceOwnerOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        space_id = view.kwargs.get('space_id')  # Changed from 'space_pk' to 'space_id'
        logger.debug(f"Checking permission for space_id: {space_id}")
        if not space_id:
            logger.warning("No space_id provided in request.")
            return False

        user = request.user
        if not user.is_authenticated:
            logger.warning("User is not authenticated.")
            return False

        # Check if user is the space creator or an admin
        try:
            space_membership = SpaceMembership.objects.get(
                space__space_id=space_id,
                user=user
            )
            is_owner = space_membership.space.created_by == user
            is_admin = space_membership.is_admin
            logger.debug(f"User {user.username} - Owner: {is_owner}, Admin: {is_admin}")
            return is_owner or is_admin
        except SpaceMembership.DoesNotExist:
            logger.warning(f"No membership found for user {user.username} in space {space_id}")
            return False

class IsSpaceMember(permissions.BasePermission):
    def has_permission(self, request, view):
        space_id = view.kwargs.get('space_id')
        logger.debug(f"Checking membership for space_id: {space_id}")
        if not space_id:
            logger.warning("No space_id provided in request.")
            return False

        user = request.user
        if not user.is_authenticated:
            logger.warning("User is not authenticated.")
            return False

        try:
            SpaceMembership.objects.get(
                space__space_id=space_id,
                user=user
            )
            logger.debug(f"User {user.username} is a member of space {space_id}")
            return True
        except SpaceMembership.DoesNotExist:
            logger.warning(f"No membership found for user {user.username} in space {space_id}")
            return False
class HasWorkspaceAccess(permissions.BasePermission):
    def has_permission(self, request, view):
        space_id = view.kwargs.get('space_id')
        logger.debug(f"Checking workspace access for space_id: {space_id}")
        if not space_id:
            logger.warning("No space_id provided in request.")
            return False

        user = request.user
        if not user.is_authenticated:
            logger.warning("User is not authenticated.")
            return False

        try:
            membership = SpaceMembership.objects.get(
                space__space_id=space_id,
                user=user
            )
            space_jwt = getattr(request, 'space_jwt', None)
            if not space_jwt:
                logger.warning(f"No SpaceJWT provided for user {user.user_id} in space {space_id}")
                return False
            if space_jwt.payload['space_id'] != str(space_id):
                logger.warning(f"SpaceJWT space_id {space_jwt.payload['space_id']} does not match requested space {space_id}")
                return False
            scope = space_jwt.payload.get('scope')
            method = request.method.lower()
            # Allow read for 'read' or higher scopes, write for 'write' or 'admin'
            if method in ['get', 'head', 'options']:
                return scope in ['read', 'write', 'admin']
            else:
                return scope in ['write', 'admin']
        except SpaceMembership.DoesNotExist:
            logger.warning(f"No membership found for user {user.username} in space {space_id}")
            return False