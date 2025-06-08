# workspace/board/models.py
from django.db import models
from workspace.models import Workspace
from outh.models import User

#bocklog
class Board(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='boards')
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Column(models.Model):
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name='columns')
    title = models.CharField(max_length=100)
    order = models.IntegerField(default=0)
     #inprgress ,forecast, done,steps
    def __str__(self):
        return self.title

class Card(models.Model):
    column = models.ForeignKey(Column, on_delete=models.CASCADE, related_name='cards')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    assignee = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_cards')
    order = models.IntegerField(default=0)
    attachment = models.FileField(upload_to='cards', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    done = models.BooleanField(default=False)  # Add the done field

    def __str__(self):
        return self.title