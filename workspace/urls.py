# workspace/urls.py
from django.urls import path, include
from . import views
from rest_framework.routers import DefaultRouter
from workspace.todo.views import TaskViewSet
from workspace.notes.views import NoteViewSet

# Define routers for todo and notes
todo_router = DefaultRouter()
todo_router.register(r'', TaskViewSet, basename='task')

notes_router = DefaultRouter()
notes_router.register(r'', NoteViewSet, basename='note')

urlpatterns = [
    path('<uuid:space_id>/', views.WorkspaceView.as_view(), name='workspace'),
    path('<uuid:space_id>/todo/', include((todo_router.urls, 'todo'), namespace='todo')),
    path('<uuid:space_id>/notes/', include((notes_router.urls, 'notes'), namespace='notes')),
    path('<uuid:space_id>/board/', include('workspace.board.urls')),  # Direct to board app
    path('<uuid:space_id>/todo/tasks/', include('workspace.todo.urls')),
    path('<uuid:space_id>/notes/notes/', include('workspace.notes.urls')),
]