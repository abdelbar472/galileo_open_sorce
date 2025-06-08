from django.urls import reverse
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.utils import timezone
import logging
from .models import Task
from .serializers import TaskSerializer
from ..models import Workspace
from space.models import Space
from space.permissions import HasWorkspaceAccess, IsSpaceOwnerOrAdmin, IsSpaceMember
from space.authentication import SpaceJWTAuthentication
from rest_framework.permissions import IsAuthenticated

logger = logging.getLogger(__name__)

class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    authentication_classes = [SessionAuthentication, JWTAuthentication, SpaceJWTAuthentication]
    permission_classes = [IsAuthenticated, IsSpaceMember]
    lookup_field = 'title'

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({'view': self})
        return context

    def get_queryset(self):
        space_id = self.kwargs.get('space_id')
        if not space_id:
            logger.error(f"No space_id provided in request at {timezone.now()}")
            return Task.objects.none()

        try:
            queryset = Task.objects.filter(workspace__space__space_id=space_id)

            priority = self.request.query_params.get('priority')
            if priority:
                if priority in dict(Task.PRIORITY_CHOICES).keys():
                    queryset = queryset.filter(priority=priority)
                else:
                    logger.warning(f"Invalid priority value '{priority}' provided at {timezone.now()}")
                    return Task.objects.none()

            order_by = self.request.query_params.get('order_by')
            if order_by == 'priority':
                queryset = queryset.order_by('priority')

            return queryset
        except Exception as e:
            logger.error(f"Error filtering tasks for space {space_id}: {str(e)} at {timezone.now()}")
            return Task.objects.none()

    def perform_create(self, serializer):
        space_id = self.kwargs.get('space_id')
        if not space_id:
            logger.error(f"No space_id provided for task creation at {timezone.now()}")
            raise Response({"error": "space_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            workspace = Workspace.objects.get(space__space_id=space_id)
            serializer.save(workspace=workspace)
            logger.info(f"Task created in workspace {workspace.id} by user {self.request.user.user_id} at {timezone.now()}")
        except Workspace.DoesNotExist:
            logger.error(f"Workspace not found for space {space_id} at {timezone.now()}")
            raise Response({"error": "Workspace not found for this space"}, status=status.HTTP_404_NOT_FOUND)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        # Check if done is True in the updated instance
        if serializer.instance.done:
            logger.info(f"Task {instance.id} (title: {instance.title}) marked as done and deleted at {timezone.now()}")
            task_list_url = reverse('task-list', kwargs={'space_id': self.kwargs.get('space_id')})
            instance.delete()
            return Response({
                "message": "Task was marked as done and deleted.",
                "task_list_url": request.build_absolute_uri(task_list_url)
            }, status=status.HTTP_204_NO_CONTENT)

        logger.info(
            f"Task {instance.id} (title: {instance.title}) updated by user {self.request.user.user_id} at {timezone.now()}")
        return Response(serializer.data)