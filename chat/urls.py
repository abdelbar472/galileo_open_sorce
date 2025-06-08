# chat/urls.py
from django.urls import path
from .views import *

urlpatterns = [
    path('<uuid:space_id>/chat-rooms/', ChatRoomListView.as_view(), name='chat-rooms-list'),
    path('<uuid:space_id>/chat-rooms/<uuid:chat_room_id>/', ChatRoomDetailView.as_view(), name='chat-room-detail'),
    path('<uuid:space_id>/chat-rooms/<uuid:chat_room_id>/members/', ChatRoomMembershipView.as_view(), name='chat-room-members'),
    path('<uuid:space_id>/chat-rooms/<uuid:chat_room_id>/members/<uuid:user_id>/', ChatRoomMembershipView.as_view(), name='chat-room-member-detail'),
    path('<uuid:space_id>/chat-rooms/<uuid:chat_room_id>/messages/', MessageView.as_view(), name='chat-messages'),
    path('<uuid:space_id>/chat-rooms/<uuid:chat_room_id>/messages/<uuid:message_id>/', MessageView.as_view(), name='message-detail'),
    path('<uuid:space_id>/chat-rooms/<uuid:chat_room_id>/stats/', RoomStatsView.as_view(), name='chat-room-stats'),
    path('health/', ChatHealthView.as_view(), name='chat-health'),

]