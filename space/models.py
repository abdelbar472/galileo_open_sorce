import uuid
from django.db import models
from django.utils import timezone
from outh.models import User

class Space(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    space_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    space_image = models.FileField(upload_to='space_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='spaces')

    def __str__(self):
        return self.name

class SpaceMembership(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='space_memberships')
    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(
        max_length=20,
        choices=(('manager', 'Manager'), ('member', 'Member'), ('guest', 'Guest')),
        default='member'
    )
    is_admin = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'space')

    def __str__(self):
        return f"{self.user} - {self.role} in {self.space}"

class Invitation(models.Model):
    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name='invitations')
    invited_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='invited_spaces')
    invited_role = models.CharField(max_length=20, choices=(('member', 'Member'), ('guest', 'Guest')))
    otp = models.CharField(max_length=6)
    otp_expiry = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Invitation for {self.invited_user} to {self.space} as {self.invited_role}"