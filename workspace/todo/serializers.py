from rest_framework import serializers
from .models import Task
from outh.models import User
from django.utils import timezone
from space.models import SpaceMembership

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['user_id', 'username', 'email']

class TaskSerializer(serializers.ModelSerializer):
    mention = UserSerializer(read_only=True)
    mention_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.none(),  # Default to empty queryset
        source='mention',
        write_only=True,
        required=False,
        allow_null=True
    )
    links = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = ['id', 'workspace', 'title', 'description', 'media', 'active', 'priority', 'mention', 'mention_id', 'created_at', 'updated_at', 'links', 'done']
        read_only_fields = ['workspace', 'created_at', 'updated_at', 'links']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dynamically set the queryset for mention_id based on space_id
        space_id = self.context.get('view', {}).kwargs.get('space_id')
        if space_id:
            self.fields['mention_id'].queryset = User.objects.filter(
                space_memberships__space__space_id=space_id,
                is_active=True
            ).distinct()

    def validate_mention_id(self, value):
        if value and not value.is_active:
            raise serializers.ValidationError("Mentioned user must be active.")

        space_id = self.context.get('view').kwargs.get('space_id')
        if not space_id:
            raise serializers.ValidationError("space_id is required to validate mention.")

        if value and not SpaceMembership.objects.filter(user=value, space__space_id=space_id).exists():
            raise serializers.ValidationError("Mentioned user must be a member of the space.")

        return value

    def get_links(self, obj):
        request = self.context.get('request')
        if request is None:
            return {}
        base_url = request.build_absolute_uri('/')[:-1]
        space_id = str(obj.workspace.space.space_id)
        return {
            'self': f"{base_url}/workspace/{space_id}/todo/{obj.title}/",
            'workspace': f"{base_url}/workspace/{space_id}/",
            'tasks': f"{base_url}/workspace/{space_id}/todo/tasks/"
        }