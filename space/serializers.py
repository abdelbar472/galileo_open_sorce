import logging

from rest_framework import serializers
from .models import *
from outh.models import User
import uuid
logger = logging.getLogger(__name__)


class SpaceSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    created_by = serializers.UUIDField(source='created_by.user_id', read_only=True)
    space_image = serializers.ImageField(required=False, allow_null=True)
    links = serializers.SerializerMethodField()

    class Meta:
        model = Space
        fields = ['space_id', 'name', 'description', 'created_at', 'updated_at', 'created_by', 'role', 'space_image', 'links']
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'space_id']

    def get_role(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            membership = SpaceMembership.objects.filter(space=obj, user=request.user).first()
            return membership.role if membership else None
        return None

    def get_links(self, obj):
        request = self.context.get('request')
        if request is None:
            return {}
        base_url = request.build_absolute_uri('/')[:-1]  # Dynamic base URL
        space_id = str(obj.space_id)
        links = {
            "invite": f"{base_url}/space/{space_id}/invite/",
            "remove_member": f"{base_url}/space/{space_id}/remove-member/",
            "change_role": f"{base_url}/space/{space_id}/change-role/",
            "space_jwt": f"{base_url}/space/{space_id}/space-jwt/",
            "space_access": f"{base_url}/space/{space_id}/tokens/",
            'chat': f"{base_url}/chat/{space_id}/chat-rooms/",
            'posts': f"{base_url}/posts/{space_id}/",
            "leave": f"{base_url}/space/{space_id}/leave/",
            'workspace': f"{base_url}/workspace/{space_id}/",

        }
        return links

    def get_fields(self):
        fields = super().get_fields()
        logger.debug(f"Serializer fields: {list(fields.keys())}")
        return fields

class MemberSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_id = serializers.UUIDField(source='user.user_id')

    class Meta:
        model = SpaceMembership
        fields = ['id', 'user_id', 'user_email', 'space', 'role', 'is_admin']
        read_only_fields = ['is_admin']

class SpaceJWTSerializer(serializers.Serializer):
    lifetime_days = serializers.IntegerField(min_value=1, max_value=30, default=7)
    scope = serializers.ChoiceField(choices=['read', 'write', 'admin'], default='read')

class InviteSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    role = serializers.ChoiceField(choices=['member', 'guest'])

    def validate_user_id(self, value):
        try:
            return User.objects.get(user_id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist.")

class JoinSerializer(serializers.Serializer):
    space_id = serializers.UUIDField()
    otp = serializers.CharField(max_length=6)

    def validate_space_id(self, value):
        try:
            return Space.objects.get(space_id=value)
        except Space.DoesNotExist:
            raise serializers.ValidationError("Space does not exist.")

class ChangeRoleSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    role = serializers.ChoiceField(choices=['member', 'guest', 'manager'])

    def validate_username(self, value):
        try:
            return User.objects.get(username=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist.")
class RemoveMemberSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    def validate_username(self, value):
        try:
            return User.objects.get(username=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist.")
class SpaceTokenSerializer(serializers.Serializer):
    token = serializers.CharField(read_only=True)
    expires_at = serializers.DateTimeField(read_only=True)
    scope = serializers.CharField(required=False, default="read write")
    expiry_days = serializers.IntegerField(required=False, default=30, write_only=True)