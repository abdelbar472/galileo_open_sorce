# workspace/board/views.py
from django.urls import reverse
from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Board, Column, Card
from .serializers import BoardSerializer, ColumnSerializer, CardSerializer
from rest_framework_simplejwt.authentication import JWTAuthentication
from space.authentication import SpaceJWTAuthentication
import logging
from django.utils import timezone
from space.permissions import HasWorkspaceAccess, IsSpaceOwnerOrAdmin, IsSpaceMember
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from ..models import Workspace
from space.models import Space
from django.db.models import Max

logger = logging.getLogger(__name__)

class BoardViewSet(viewsets.ModelViewSet):
    queryset = Board.objects.all()
    serializer_class = BoardSerializer
    authentication_classes = [SessionAuthentication, JWTAuthentication, SpaceJWTAuthentication]
    permission_classes = [IsAuthenticated, IsSpaceMember]
    lookup_field = 'name'

    def get_queryset(self):
        space_id = self.kwargs.get('space_id')
        if not space_id:
            logger.error(f"No space_id provided in request at {timezone.now()}")
            return Board.objects.none()
        try:
            return Board.objects.filter(workspace__space__space_id=space_id)
        except Exception as e:
            logger.error(f"Error filtering boards for space {space_id}: {str(e)} at {timezone.now()}")
            return Board.objects.none()

    def perform_create(self, serializer):
        space_id = self.kwargs.get('space_id')
        if not space_id:
            logger.error(f"No space_id provided for board creation at {timezone.now()}")
            raise Response({"error": "space_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            workspace = Workspace.objects.get(space__space_id=space_id)
            serializer.save(workspace=workspace)
            logger.info(f"Board created in workspace {workspace.id} by user {self.request.user.user_id} at {timezone.now()}")
        except Workspace.DoesNotExist:
            logger.error(f"Workspace not found for space {space_id} at {timezone.now()}")
            raise Response({"error": "Workspace not found for this space"}, status=status.HTTP_404_NOT_FOUND)

class ColumnViewSet(viewsets.ModelViewSet):
    queryset = Column.objects.all()
    serializer_class = ColumnSerializer
    authentication_classes = [SessionAuthentication, JWTAuthentication, SpaceJWTAuthentication]
    permission_classes = [IsAuthenticated, IsSpaceMember]
    lookup_field = 'title'
    lookup_url_kwarg = 'title'

    def get_queryset(self):
        space_id = self.kwargs.get('space_id')
        board_name = self.kwargs.get('name')
        if not space_id or not board_name:
            logger.error(f"Missing space_id or board name in request at {timezone.now()}")
            return Column.objects.none()
        try:
            workspace = Workspace.objects.get(space__space_id=space_id)
            board = Board.objects.get(name=board_name, workspace=workspace)
            return Column.objects.filter(board=board)
        except Workspace.DoesNotExist:
            logger.error(f"Workspace not found for space {space_id} at {timezone.now()}")
            return Column.objects.none()
        except Board.DoesNotExist:
            logger.error(f"Board {board_name} not found in space {space_id} at {timezone.now()}")
            return Column.objects.none()
        except Exception as e:
            logger.error(f"Error filtering columns for space {space_id}, board {board_name}: {str(e)} at {timezone.now()}")
            return Column.objects.none()

    def perform_create(self, serializer):
        space_id = self.kwargs.get('space_id')
        board_name = self.kwargs.get('name')
        if not space_id or not board_name:
            logger.error(f"No space_id or board name provided for column creation at {timezone.now()}")
            raise Response({"error": "space_id and board name are required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            workspace = Workspace.objects.get(space__space_id=space_id)
            board = Board.objects.get(name=board_name, workspace=workspace)
            serializer.save(board=board)
            logger.info(f"Column created in board {board.id} by user {self.request.user.user_id} at {timezone.now()}")
        except Workspace.DoesNotExist:
            logger.error(f"Workspace not found for space {space_id} at {timezone.now()}")
            raise Response({"error": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)
        except Board.DoesNotExist:
            logger.error(f"Board {board_name} not found at {timezone.now()}")
            raise Response({"error": "Board not found"}, status=status.HTTP_404_NOT_FOUND)

class CardViewSet(viewsets.ModelViewSet):
    queryset = Card.objects.all()
    serializer_class = CardSerializer
    authentication_classes = [SessionAuthentication, JWTAuthentication, SpaceJWTAuthentication]
    permission_classes = [IsAuthenticated, IsSpaceMember]
    lookup_field = 'title'
    lookup_url_kwarg = 'card_title'

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({'view': self})
        return context

    def get_queryset(self):
        space_id = self.kwargs.get('space_id')
        board_name = self.kwargs.get('name')
        column_title = self.kwargs.get('title')
        if not space_id or not board_name or not column_title:
            logger.error(f"Missing space_id, board name, or column title in request at {timezone.now()}")
            return Card.objects.none()
        try:
            workspace = Workspace.objects.get(space__space_id=space_id)
            board = Board.objects.get(name=board_name, workspace=workspace)
            column = Column.objects.get(title=column_title, board=board)
            return Card.objects.filter(column=column)
        except Workspace.DoesNotExist:
            logger.error(f"Workspace not found for space {space_id} at {timezone.now()}")
            return Card.objects.none()
        except Board.DoesNotExist:
            logger.error(f"Board {board_name} not found in space {space_id} at {timezone.now()}")
            return Card.objects.none()
        except Column.DoesNotExist:
            logger.error(f"Column {column_title} not found in board {board_name} at {timezone.now()}")
            return Card.objects.none()
        except Exception as e:
            logger.error(f"Error filtering cards for space {space_id}, board {board_name}, column {column_title}: {str(e)} at {timezone.now()}")
            return Card.objects.none()

    def perform_create(self, serializer):
        space_id = self.kwargs.get('space_id')
        board_name = self.kwargs.get('name')
        column_title = self.kwargs.get('title')
        if not space_id or not board_name or not column_title:
            logger.error(f"No space_id, board name, or column title provided for card creation at {timezone.now()}")
            raise Response({"error": "space_id, board name, and column title are required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            workspace = Workspace.objects.get(space__space_id=space_id)
            board = Board.objects.get(name=board_name, workspace=workspace)
            column = Column.objects.get(title=column_title, board=board)
            serializer.save(column=column)
            logger.info(f"Card created in column {column.id} by user {self.request.user.user_id} at {timezone.now()}")
        except Workspace.DoesNotExist:
            logger.error(f"Workspace not found for space {space_id} at {timezone.now()}")
            raise Response({"error": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)
        except Board.DoesNotExist:
            logger.error(f"Board {board_name} not found at {timezone.now()}")
            raise Response({"error": "Board not found"}, status=status.HTTP_404_NOT_FOUND)
        except Column.DoesNotExist:
            logger.error(f"Column {column_title} not found at {timezone.now()}")
            raise Response({"error": "Column not found"}, status=status.HTTP_404_NOT_FOUND)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        # Update order if moving to a new column
        if 'column_id' in request.data and serializer.instance.column.title != request.data['column_id']:
            target_column_title = request.data['column_id']  # Expecting column title now
            try:
                space_id = self.kwargs.get('space_id')
                board_name = self.kwargs.get('name')
                workspace = Workspace.objects.get(space__space_id=space_id)
                board = Board.objects.get(name=board_name, workspace=workspace)
                target_column = Column.objects.get(title=target_column_title, board=board)
                max_order = Card.objects.filter(column=target_column).aggregate(Max('order'))['order__max'] or 0
                serializer.validated_data['order'] = max_order + 1
                logger.info(f"Card {instance.id} (title: {instance.title}) moved from column {instance.column.title} to column {target_column_title} with order {max_order + 1} by user {self.request.user.user_id} at {timezone.now()}")
            except Column.DoesNotExist:
                logger.error(f"Target column {target_column_title} not found for board {board_name} at {timezone.now()}")
                raise Response({"error": "Target column not found"}, status=status.HTTP_404_NOT_FOUND)
            except Workspace.DoesNotExist:
                logger.error(f"Workspace not found for space {space_id} at {timezone.now()}")
                raise Response({"error": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)
            except Board.DoesNotExist:
                logger.error(f"Board {board_name} not found at {timezone.now()}")
                raise Response({"error": "Board not found"}, status=status.HTTP_404_NOT_FOUND)

        self.perform_update(serializer)

        # Check if done is True in the updated instance
        if serializer.instance.done:
            logger.info(f"Card {instance.id} (title: {instance.title}) marked as done and deleted at {timezone.now()}")
            card_list_url = reverse('card-list', kwargs={'space_id': self.kwargs.get('space_id'), 'name': self.kwargs.get('name'), 'title': self.kwargs.get('title')})
            instance.delete()
            return Response({
                "message": "Card was marked as done and deleted.",
                "card_list_url": request.build_absolute_uri(card_list_url)
            }, status=status.HTTP_204_NO_CONTENT)

        logger.info(f"Card {instance.id} (title: {instance.title}) updated by user {self.request.user.user_id} at {timezone.now()}")
        return Response(serializer.data)