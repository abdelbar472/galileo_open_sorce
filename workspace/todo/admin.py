from django.contrib import admin
from workspace.todo.models import Task  # Use correct case - Task, not task

# Register the Task model
admin.site.register(Task)