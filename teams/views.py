from django.utils.functional import SimpleLazyObject
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from .models import *
from .serializers import *

import logging
logger = logging.getLogger(__name__)




class ListTeamsView(generics.ListAPIView):
    #keep this as it is
    permission_classes = [permissions.IsAuthenticated,permissions.IsAdminUser]  # Only allow admin users to access this view
    serializer_class = TeamSerializer

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            raise ValueError("User is not authenticated.")
        if not isinstance(user, User):
            raise ValueError("Authenticated user is not a valid User instance.")
        return Team.objects.filter(members__user=user)

class RemoveMemberView(APIView):
    """
    API to remove a member from a team. Only the manager can perform this action.
    """
    permission_classes = [IsAuthenticated, permissions.IsAdminUser]  # Only allow admin users to access this view

    def delete(self, request, team_id):
        # Get the team
        try:
            team = Team.objects.get(id=team_id)
        except Team.DoesNotExist:
            return Response(
                {"error": "Team not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if the requesting user is the manager of the team
        try:
            manager_member = Member.objects.get(team=team, user=request.user)
            if not manager_member.is_admin:  # Check is_admin instead of is_manager()
                raise PermissionDenied("Only the manager can remove members.")
        except Member.DoesNotExist:
            raise PermissionDenied("You are not a member of this team.")

        member_id = request.data.get('member_id')
        try:
            member_to_remove = Member.objects.get(member_id=member_id, team=team)
        except Member.DoesNotExist:
            return Response(
                {"error": "Member not found in this team."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Prevent the manager from removing themselves
        if member_to_remove.user == request.user:
            return Response(
                {"error": "You cannot remove yourself as the manager."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Remove the member
        member_to_remove.delete()
        return Response(
            {"message": f"Member {member_to_remove.user.username} removed from the team."},
            status=status.HTTP_200_OK,
        )

#add this to soace
class TeamMembersView(APIView):
    """
    API to view all members of a team.
    """
    permission_classes = [IsAuthenticated, permissions.IsAdminUser]  # Only allow admin users to access this view

    def get(self, request, team_id):
        try:
            team = Team.objects.get(id=team_id)
        except Team.DoesNotExist:
            return Response(
                {"error": "Team not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if the user is a member of the team
        if not Member.objects.filter(team=team, user=request.user).exists():
            return Response(
                {"error": "You are not a member of this team."},
                status=status.HTTP_403_FORBIDDEN,
            )

        members = Member.objects.filter(team=team)
        serializer = MemberSerializer(members, many=True)
        return Response(serializer.data)