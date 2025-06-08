# serializers.py
from rest_framework import serializers
from .models import Post

class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ['id', 'space', 'user', 'content', 'attachment', 'platforms', 'scheduled_time', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at' ,'space']


class PostCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Post
        fields = ['content', 'attachment', 'platforms', 'scheduled_time', 'status']
        read_only_fields = ['created_at']

    def validate_platforms(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Platforms must be a list")
        return value

    def create(self, validated_data):
        # Ensure user and space are set by the view
        user = validated_data.pop('user', None)
        space = validated_data.pop('space', None)
        if not user or not space:
            raise serializers.ValidationError("User and space must be provided by the view")
        return Post.objects.create(user=user, space=space, **validated_data)

class PostUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ['content', 'attachment', 'platforms', 'scheduled_time', 'status']