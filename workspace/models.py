from django.db import models
from space.models import Space  # Link to Space model
from outh.models import User

class Workspace(models.Model):
    space = models.OneToOneField(Space, on_delete=models.CASCADE, related_name='workspace')
    name = models.CharField(max_length=100, default='Default Workspace')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} (Space: {self.space.name})"