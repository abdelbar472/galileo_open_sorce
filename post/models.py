
# models.py
from django.db import models
from django.utils import timezone
import uuid
from outh.models import User
from space.models import Space

class Post(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("scheduled", "Scheduled"),
        ("published", "Published"),
        ("archived", "Archived"),
    ]

    PLATFORM_CHOICES = [
        ("twitter", "Twitter"),
        ("facebook", "Facebook"),
        ("linkedin", "LinkedIn"),
        ("instagram", "Instagram"),

    ]
    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name='posts')
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    attachment = models.FileField(upload_to='attachments', blank=True, null=True)
    platforms = models.JSONField(default=list)  # ["twitter", "facebook"]
    scheduled_time = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")  # <-- ADD THIS
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) #history

    def __str__(self):
        return self.content[:50]
