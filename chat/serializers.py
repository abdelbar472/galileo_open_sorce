# chat/serializers.py
from rest_framework import serializers
from .models import ChatRoom, ChatRoomMembership

class ChatRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatRoom
        fields = ['id', 'name', 'space', 'team', 'created_at', 'is_active']
        read_only_fields = ['id', 'created_at']

class ChatRoomMembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatRoomMembership
        fields = ['id', 'chat_room', 'user', 'created_at', 'is_admin']
        read_only_fields = ['id', 'created_at']

class MessageSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    room = serializers.CharField(read_only=True)
    user = serializers.CharField(read_only=True)
    content = serializers.CharField(required=True)
    created_at = serializers.DateTimeField(read_only=True)