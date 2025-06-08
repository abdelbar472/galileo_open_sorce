from django.urls import path, include
from .views import NoteViewSet

urlpatterns = [
    path('', NoteViewSet.as_view({'get': 'list', 'post': 'create'}), name='note-list'),
    path('<str:title>/', NoteViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='note-detail'),
]