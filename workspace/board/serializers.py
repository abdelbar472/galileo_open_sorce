# workspace/board/serializers.py
from rest_framework import serializers
from .models import Board, Column, Card
from outh.models import User
from space.models import SpaceMembership
from ..models import Workspace

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['user_id', 'username', 'email']

class CardSerializer(serializers.ModelSerializer):
    assignee = UserSerializer(read_only=True)
    assignee_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.none(),
        source='assignee',
        write_only=True,
        required=False,
        allow_null=True
    )
    column = serializers.PrimaryKeyRelatedField(read_only=True)
    column_title = serializers.SlugRelatedField(  # Renamed from column_id to column_title
        queryset=Column.objects.none(),
        slug_field='title',
        source='column',
        write_only=True,
        required=True  # Required for POST
    )

    class Meta:
        model = Card
        fields = ['id', 'column', 'column_title', 'title', 'description', 'assignee', 'assignee_id', 'order', 'created_at', 'updated_at', 'done']
        read_only_fields = ['created_at', 'updated_at', 'column']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'view' in self.context and hasattr(self.context['view'], 'kwargs'):
            space_id = self.context['view'].kwargs.get('space_id')
            board_name = self.context['view'].kwargs.get('name')
            if space_id:
                try:
                    workspace = Workspace.objects.get(space__space_id=space_id)
                    self.fields['assignee_id'].queryset = User.objects.filter(
                        space_memberships__space__space_id=space_id,
                        is_active=True
                    ).distinct()
                    if board_name:
                        self.fields['column_title'].queryset = Column.objects.filter(
                            board__name=board_name,
                            board__workspace=workspace
                        )
                except Workspace.DoesNotExist:
                    logger.error(f"Workspace not found for space {space_id} at {timezone.now()}")
                    self.fields['assignee_id'].queryset = User.objects.none()
                    self.fields['column_title'].queryset = Column.objects.none()

    def validate_assignee_id(self, value):
        if value and not value.is_active:
            raise serializers.ValidationError("Assigned user must be active.")
        space_id = self.context.get('view', {}).kwargs.get('space_id')
        if not space_id:
            raise serializers.ValidationError("space_id is required to validate assignee.")
        if value and not SpaceMembership.objects.filter(user=value, space__space_id=space_id).exists():
            raise serializers.ValidationError("Assigned user must be a member of the space.")
        return value

    def validate_column_title(self, value):
        if value:
            space_id = self.context.get('view', {}).kwargs.get('space_id')
            board_name = self.context.get('view', {}).kwargs.get('name')
            if not space_id or not board_name:
                raise serializers.ValidationError("space_id and board name are required to validate column.")
            try:
                workspace = Workspace.objects.get(space__space_id=space_id)
                board = Board.objects.get(name=board_name, workspace=workspace)
                if not Column.objects.filter(title=value, board=board).exists():
                    raise serializers.ValidationError("Target column must belong to the specified board.")
            except (Workspace.DoesNotExist, Board.DoesNotExist):
                raise serializers.ValidationError("Workspace or board not found.")
        return value

class ColumnSerializer(serializers.ModelSerializer):
    cards = CardSerializer(many=True, read_only=True)

    class Meta:
        model = Column
        fields = ['id', 'board', 'title', 'order', 'cards']

class BoardSerializer(serializers.ModelSerializer):
    columns = ColumnSerializer(many=True, read_only=True)

    class Meta:
        model = Board
        fields = ['id', 'workspace', 'name', 'created_at', 'updated_at', 'columns']
        read_only_fields = ['created_at', 'updated_at']