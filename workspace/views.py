# workspace/views.py
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.utils import timezone
import logging
from rest_framework.permissions import IsAuthenticated

from .models import Workspace
from .serializers import WorkspaceSerializer
from space.models import Space, SpaceMembership
from space.permissions import IsSpaceOwnerOrAdmin, HasWorkspaceAccess,IsSpaceMember
from space.authentication import SpaceJWTAuthentication

logger = logging.getLogger(__name__)




class WorkspaceView(generics.GenericAPIView):
    queryset = Workspace.objects.all()
    serializer_class = WorkspaceSerializer
    authentication_classes = [SessionAuthentication, JWTAuthentication, SpaceJWTAuthentication]
    permission_classes = [IsAuthenticated,  IsSpaceMember]

    def post(self, request, space_id):
        try:
            space = Space.objects.get(space_id=space_id)
        except Space.DoesNotExist:
            logger.error(f"Space {space_id} not found at {timezone.now()}")
            return Response({"error": "Space not found"}, status=404)

        # Check if workspace already exists
        if Workspace.objects.filter(space=space).exists():
            logger.warning(f"Workspace already exists for space {space_id}")
            return Response({"error": "Workspace already exists for this space"}, status=400)

        # Use space primary key field correctly
        serializer = self.get_serializer(
            data={'space': space.pk, 'name': request.data.get('name', 'Default Workspace')},
            context={'request': request})

        if serializer.is_valid():
            serializer.save()
            logger.info(f"Workspace created for space {space_id} by user {request.user.username} at {timezone.now()}")
            return Response(serializer.data, status=201)
        logger.error(f"Workspace creation failed: {serializer.errors} at {timezone.now()}")
        return Response(serializer.errors, status=400)

    def get(self, request, space_id):
        try:
            space = Space.objects.get(space_id=space_id)
            # Check membership for better error messages
            if not SpaceMembership.objects.filter(space=space, user=request.user).exists():
                return Response({"error": "You are not a member of this space"}, status=403)

            try:
                workspace = Workspace.objects.get(space=space)
                serializer = self.get_serializer(workspace, context={'request': request})
                return Response(serializer.data, status=200)
            except Workspace.DoesNotExist:
                logger.error(f"Workspace not found for space {space_id} at {timezone.now()}")
                return Response({"error": "Workspace not found"}, status=404)
        except Space.DoesNotExist:
            logger.error(f"Space {space_id} not found at {timezone.now()}")
            return Response({"error": "Space not found"}, status=404)