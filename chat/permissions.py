# chat/permissions.py
from rest_framework import permissions
from .models import ChatRoom, ChatRoomMembership
from space.models import SpaceMembership


class HasSpaceAccess(permissions.BasePermission):
    """
    Permission to check if user has access to the space
    """

    def has_permission(self, request, view):
        space_id = view.kwargs.get('space_id')

        # Check if user is authenticated
        if not request.user.is_authenticated:
            return False

        # Check if user is a member of the space
        return SpaceMembership.objects.filter(
            user=request.user,
            space__space_id=space_id
        ).exists()


class IsChatRoomMember(permissions.BasePermission):
    """
    Permission to check if user is a member of the chat room
    """

    def has_permission(self, request, view):
        space_id = view.kwargs.get('space_id')
        chat_room_id = view.kwargs.get('chat_room_id')

        # Check if user is authenticated
        if not request.user.is_authenticated:
            return False

        # Check if chat room exists in this space
        try:
            chat_room = ChatRoom.objects.get(id=chat_room_id, space__space_id=space_id)
        except ChatRoom.DoesNotExist:
            return False

        # Check if user is a member of the space
        if SpaceMembership.objects.filter(user=request.user, space=chat_room.space).exists():
            return True

        # If team-specific chat, check team membership
        if chat_room.team:
            from teams.models import Member
            if Member.objects.filter(user=request.user, team=chat_room.team).exists():
                return True

        # Check direct chat room membership
        return ChatRoomMembership.objects.filter(chat_room=chat_room, user=request.user).exists()