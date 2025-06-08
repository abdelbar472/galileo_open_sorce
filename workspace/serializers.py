# workspace/serializers.py
from rest_framework import serializers
from .models import Workspace

class WorkspaceSerializer(serializers.ModelSerializer):
    links = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = ['id', 'space', 'name', 'created_at', 'updated_at', 'links']
        read_only_fields = ['created_at', 'updated_at']

    def get_links(self, obj):
        request = self.context.get('request')
        if request is None:
            return {}
        base_url = request.build_absolute_uri('/')[:-1]
        space_id = str(obj.space.space_id)
        return {
            'tasks': f"{base_url}/workspace/{space_id}/todo/",
            'boards': f"{base_url}/workspace/{space_id}/board/",
            'notes': f"{base_url}/workspace/{space_id}/notes/",
        }