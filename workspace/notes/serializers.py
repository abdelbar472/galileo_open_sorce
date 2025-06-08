from rest_framework import serializers
from .models import Note
from outh.models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['user_id', 'username', 'email']

class NoteSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    links = serializers.SerializerMethodField()
    attachment = serializers.FileField(allow_empty_file=True, required=False)

    class Meta:
        model = Note
        fields = [
            'id',
            'workspace',
            'user',
            'username',
            'title',
            'content',
            'attachment',
            'created_at',
            'updated_at',
            'links'
        ]
        read_only_fields = ['created_at', 'updated_at', 'username', 'user', 'workspace']

    def get_links(self, obj):
        request = self.context.get('request')
        if request is None:
            return {}
        if isinstance(obj, dict):
            return {}  # Return empty links during creation
        else:
            space_id = str(obj.workspace.space.space_id)
            base_url = request.build_absolute_uri('/')[:-1]
            return {
                'self': f"{base_url}/workspace/{space_id}/notes/{obj.title}/",
                'all_notes': f"{base_url}/workspace/{space_id}/notes/",
                'workspace': f"{base_url}/workspace/{space_id}/"
            }