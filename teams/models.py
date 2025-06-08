# teams/models.py
import uuid
from django.db import models
from django.utils import timezone
from datetime import timedelta
from outh.models import User
from space.models import Space

class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    team_image = models.FileField(upload_to='team_images', blank=True, null=True)
    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name='teams', null=True)

    def __str__(self):
        return self.name

    def add_manager(self, user):
        Member.objects.create(user=user, team=self, role='manager', is_admin=True)

ROLE_CHOICES = [
    ('manager', 'Manager'),
    ('member', 'Member'),
    ('guest', 'Guest'),
]

class Member(models.Model):
    member_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='team_memberships')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='members')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    is_admin = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.username} - {self.team.name}"

    class Meta:
        unique_together = ('user', 'team')
        indexes = [
            models.Index(fields=['user', 'team']),
        ]