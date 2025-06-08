# workspace/notes/models.py
from django.db import models
from workspace.models import Workspace
from outh.models import User

class Note(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='notes')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='notes')
    title = models.CharField(max_length=200)
    content = models.TextField()
    attachment = models.FileField(upload_to='notes', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title