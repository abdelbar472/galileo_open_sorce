from django.db import models
from workspace.models import Workspace
from outh.models import User
from django.utils import timezone  # Add this for datetime fields

class Task(models.Model):
    PRIORITY_CHOICES = [
        ('red', 'Red'),
        ('green', 'Green'),
        ('blue', 'Blue'),
        ('white', 'White'),
    ]
    workspace = models.ForeignKey(Workspace, related_name='tasks', on_delete=models.CASCADE)
    title = models.CharField(max_length=250)
    description = models.TextField(max_length=250, null=True, blank=True)
    media = models.FileField(upload_to='todo', null=True, blank=True)
    active = models.BooleanField(default=False)
    priority = models.CharField(max_length=25, choices=PRIORITY_CHOICES, null=True, blank=True)
    mention = models.ForeignKey(User, related_name='mention', blank=True, null=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)  # Change from auto_now_add
    updated_at = models.DateTimeField(auto_now=True)
    done = models.BooleanField(default=False)
    def __str__(self):
        return self.title
    class Meta:
        #make title unique in workspace
        unique_together = ('workspace', 'title')