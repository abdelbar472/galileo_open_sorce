from rest_framework import serializers
from .models import *

class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ['id', 'name', 'description', 'team_image']
        read_only_fields = ['id', 'otp', 'created_at']

class TeamCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new team."""
    class Meta:
        model = Team
        fields = ['name', 'description', 'team_image']

class JoinTeamSerializer(serializers.Serializer):
    """Serializer for joining a team via OTP."""
    otp = serializers.CharField(max_length=6)

class MemberSerializer(serializers.ModelSerializer):
    """Serializer for viewing team members."""
    user = serializers.StringRelatedField()  # Display username instead of user ID
    role = serializers.CharField(read_only=True)  # Fixed: Removed source="role.name"

    class Meta:
        model = Member
        fields = ['id', 'user', 'role', 'date_joined']

class RemoveMemberSerializer(serializers.Serializer):
    member_id = serializers.UUIDField()