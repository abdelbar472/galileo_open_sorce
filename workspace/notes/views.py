from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Note
from .serializers import NoteSerializer
from rest_framework_simplejwt.authentication import JWTAuthentication
from space.authentication import SpaceJWTAuthentication
import logging
from django.utils import timezone
from space.permissions import HasWorkspaceAccess, IsSpaceOwnerOrAdmin, IsSpaceMember
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from ..models import Workspace
from space.models import Space
from rest_framework.exceptions import ValidationError
from outh.models import User


logger = logging.getLogger(__name__)

class NoteViewSet(viewsets.ModelViewSet):
    queryset = Note.objects.all()
    serializer_class = NoteSerializer
    authentication_classes = [SessionAuthentication, JWTAuthentication, SpaceJWTAuthentication]
    permission_classes = [IsAuthenticated, IsSpaceMember]
    lookup_field = 'title'

    def get_queryset(self):
        space_id = self.kwargs.get('space_id')
        if not space_id:
            logger.error(f"No space_id provided in request at {timezone.now()} by user {self.request.user.user_id}")
            return Note.objects.none()
        try:
            workspace = Workspace.objects.get(space__space_id=space_id)
            return Note.objects.filter(workspace=workspace)
        except Workspace.DoesNotExist:
            logger.error(f"Workspace not found for space {space_id} at {timezone.now()} by user {self.request.user.user_id}")
            return Note.objects.none()
        except Exception as e:
            logger.error(f"Error filtering notes for space {space_id}: {str(e)} at {timezone.now()} by user {self.request.user.user_id}")
            return Note.objects.none()

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user != self.request.user and not self.request.user.is_staff:
            logger.warning(f"Unauthorized access attempt to note {instance.title} by user {self.request.user.user_id} at {timezone.now()}")
            return Response({"error": "You do not have permission to view this note"}, status=status.HTTP_403_FORBIDDEN)
        return super().retrieve(request, *args, **kwargs)

    def perform_create(self, serializer):
        space_id = self.kwargs.get('space_id')
        if not space_id:
            logger.error(f"No space_id provided for note creation at {timezone.now()} by user {self.request.user.user_id}")
            return Response({"error": "space_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            workspace = Workspace.objects.get(space__space_id=space_id)
            # Log attachment for debugging
            attachment = self.request.FILES.get('attachment')
            logger.info(f"Attachment in request: {attachment} for note creation by user {self.request.user.user_id} at {timezone.now()}")
            serializer.save(
                workspace=workspace,
                user=self.request.user,
                attachment=attachment
            )
            logger.info(f"Note created in workspace {workspace.name} by user {self.request.user.user_id} at {timezone.now()}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Workspace.DoesNotExist:
            logger.error(f"Workspace not found for space {space_id} at {timezone.now()} by user {self.request.user.user_id}")
            return Response({"error": "Workspace not found for this space"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error creating note for space {space_id}: {str(e)} at {timezone.now()} by user {self.request.user.user_id}")
            return Response({"error": "An unexpected error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def perform_update(self, serializer):
        space_id = self.kwargs.get('space_id')
        instance = self.get_object()
        if instance.user != self.request.user and not self.request.user.is_staff:
            logger.warning(f"Unauthorized update attempt to note {instance.title} by user {self.request.user.user_id} at {timezone.now()}")
            return Response({"error": "You do not have permission to update this note"}, status=status.HTTP_403_FORBIDDEN)
        try:
            workspace = Workspace.objects.get(space__space_id=space_id)
            # Log attachment for debugging
            attachment = self.request.FILES.get('attachment')
            logger.info(f"Attachment in request: {attachment} for note update by user {self.request.user.user_id} at {timezone.now()}")
            serializer.save(
                workspace=workspace,
                user=self.request.user,
                attachment=attachment
            )
            logger.info(f"Note {instance.title} updated in workspace {workspace.name} by user {self.request.user.user_id} at {timezone.now()}")
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Workspace.DoesNotExist:
            logger.error(f"Workspace not found for space {space_id} at {timezone.now()} by user {self.request.user.user_id}")
            return Response({"error": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error updating note for space {space_id}: {str(e)} at {timezone.now()} by user {self.request.user.user_id}")
            return Response({"error": "An unexpected error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def perform_destroy(self, instance):
        space_id = self.kwargs.get('space_id')
        if instance.user != self.request.user and not self.request.user.is_staff:
            logger.warning(f"Unauthorized delete attempt to note {instance.title} by user {self.request.user.user_id} at {timezone.now()}")
            return Response({"error": "You do not have permission to delete this note"}, status=status.HTTP_403_FORBIDDEN)
        try:
            workspace = Workspace.objects.get(space__space_id=space_id)
            logger.info(f"Note {instance.title} deleted from workspace {workspace.name} by user {self.request.user.user_id} at {timezone.now()}")
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Workspace.DoesNotExist:
            logger.error(f"Workspace not found for space {space_id} at {timezone.now()} by user {self.request.user.user_id}")
            return Response({"error": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)
