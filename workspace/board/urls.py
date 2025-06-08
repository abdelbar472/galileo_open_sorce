# workspace/board/urls.py
from django.urls import path
from .views import BoardViewSet, ColumnViewSet, CardViewSet

urlpatterns = [
    # Boards
    path('', BoardViewSet.as_view({'get': 'list', 'post': 'create'}), name='board-list'),
    path('<str:name>/',BoardViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}),name='board-detail'),

    # Columns
    path('<str:name>/columns/', ColumnViewSet.as_view({'get': 'list', 'post': 'create'}), name='column-list'),
    path('<str:name>/columns/<str:title>/',ColumnViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}),name='column-detail'),

    # Cards
    path('<str:name>/columns/<str:title>/cards/', CardViewSet.as_view({'get': 'list', 'post': 'create'}),name='card-list'),
    path('<str:name>/columns/<str:title>/cards/<str:card_title>/',CardViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}),name='card-detail'),
]