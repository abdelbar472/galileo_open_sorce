# chat/views.py
from datetime import datetime
import json
import uuid
import logging
from cassandra.cqlengine import connection
from cassandra import ConsistencyLevel
from rest_framework import status, generics
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.shortcuts import get_object_or_404, render
from outh.models import User  # Keep your custom User import
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings  # Correct import
from .models import ChatRoom, ChatRoomMembership, MessageScylla
from .serializers import ChatRoomSerializer, ChatRoomMembershipSerializer, MessageSerializer
from .permissions import *
from .services.redis_service import redis_chat_service
from space.models import Space, SpaceMembership  # Adjust if your app is named differently



logger = logging.getLogger(__name__)


class ChatRoomListView(generics.ListCreateAPIView):
    """
    List and create chat rooms for a space
    """
    serializer_class = ChatRoomSerializer
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated, HasSpaceAccess]

    def get_queryset(self):
        space_id = self.kwargs.get('space_id')
        if not SpaceMembership.objects.filter(
                user=self.request.user,
                space__space_id=space_id
        ).exists():
            return ChatRoom.objects.none()
        return ChatRoom.objects.filter(space__space_id=space_id)

    def perform_create(self, serializer):
        space_id = self.kwargs.get('space_id')
        space = get_object_or_404(Space, space_id=space_id)
        if not SpaceMembership.objects.filter(
                user=self.request.user,
                space=space,
                is_admin=True
        ).exists():
            raise PermissionDenied("Only space admins can create chat rooms")
        serializer.save(space=space)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        for room_data in response.data:
            room_id = room_data['id']
            room_stats = redis_chat_service.get_room_stats(room_id)
            room_data['stats'] = room_stats
        return response

class ChatRoomDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a chat room with real-time stats
    """
    serializer_class = ChatRoomSerializer
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated, IsChatRoomMember]
    lookup_field = 'id'
    lookup_url_kwarg = 'chat_room_id'

    def get_queryset(self):
        space_id = self.kwargs.get('space_id')
        return ChatRoom.objects.filter(space__space_id=space_id)

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        room_id = kwargs.get('chat_room_id')
        response.data['stats'] = redis_chat_service.get_room_stats(room_id)
        response.data['online_users'] = redis_chat_service.get_online_users(room_id)
        response.data['typing_users'] = redis_chat_service.get_typing_users(room_id)
        return response

    def destroy(self, request, *args, **kwargs):
        room_id = kwargs.get('chat_room_id')
        redis_chat_service.cleanup_room(room_id)
        return super().destroy(request, *args, **kwargs)

class ChatRoomMembershipView(APIView):
    """
    Add or remove members from a chat room
    """
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated, IsChatRoomMember]

    def post(self, request, space_id, chat_room_id):
        try:
            chat_room = ChatRoom.objects.get(id=chat_room_id, space__space_id=space_id)
        except ChatRoom.DoesNotExist:
            return Response({"error": "Chat room not found"}, status=status.HTTP_404_NOT_FOUND)

        is_space_admin = SpaceMembership.objects.filter(
            user=self.request.user,
            space=chat_room.space,
            is_admin=True
        ).exists()

        is_chat_admin = ChatRoomMembership.objects.filter(
            user=self.request.user,
            chat_room=chat_room,
            is_admin=True
        ).exists()

        if not (is_space_admin or is_chat_admin):
            return Response(
                {"error": "Only space or chat room admins can add members"},
                status=status.HTTP_403_FORBIDDEN
            )

        user_id = request.data.get('user_id')
        if not user_id:
            return Response({"error": "User ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(user_id=user_id)
            if not SpaceMembership.objects.filter(user=user, space=chat_room.space).exists():
                return Response(
                    {"error": "User is not a member of this space"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        membership, created = ChatRoomMembership.objects.get_or_create(
            chat_room=chat_room,
            user=user,
            defaults={'is_admin': request.data.get('is_admin', False)}
        )

        if not created:
            membership.is_admin = request.data.get('is_admin', membership.is_admin)
            membership.save()

        return Response({
            "id": str(membership.id),
            "user_id": str(user.user_id),
            "is_admin": membership.is_admin
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    def delete(self, request, space_id, chat_room_id, user_id):
        try:
            chat_room = ChatRoom.objects.get(id=chat_room_id, space__space_id=space_id)
        except ChatRoom.DoesNotExist:
            return Response({"error": "Chat room not found"}, status=status.HTTP_404_NOT_FOUND)

        is_space_admin = SpaceMembership.objects.filter(
            user=self.request.user,
            space=chat_room.space,
            is_admin=True
        ).exists()

        is_chat_admin = ChatRoomMembership.objects.filter(
            user=self.request.user,
            chat_room=chat_room,
            is_admin=True
        ).exists()

        if not (is_space_admin or is_chat_admin):
            return Response(
                {"error": "Only space or chat room admins can remove members"},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            user = User.objects.get(user_id=user_id)
            membership = ChatRoomMembership.objects.get(chat_room=chat_room, user=user)
            membership.delete()
            redis_chat_service.set_user_offline(chat_room_id, str(user_id))
            return Response(status=status.HTTP_204_NO_CONTENT)
        except (User.DoesNotExist, ChatRoomMembership.DoesNotExist):
            return Response({"error": "Membership not found"}, status=status.HTTP_404_NOT_FOUND)


class MessageView(APIView):
    """
    Enhanced message handling with pagination and better caching
    """
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated, IsChatRoomMember]

    def get(self, request, space_id, chat_room_id):
        """Retrieve messages with cursor-based pagination"""
        try:
            chat_room = ChatRoom.objects.get(id=chat_room_id, space__space_id=space_id)
        except ChatRoom.DoesNotExist:
            logger.error(f"Chat room {chat_room_id} not found for space {space_id}")
            return Response({"error": "Chat room not found"}, status=status.HTTP_404_NOT_FOUND)

        # Pagination parameters
        try:
            limit = min(int(request.query_params.get('limit', 50)), 100)  # Cap at 100
            before_time = request.query_params.get('before')

            if before_time:
                before_time = datetime.fromisoformat(before_time.replace('Z', '+00:00'))
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid pagination parameters: {str(e)}")
            return Response({"error": "Invalid pagination parameters"}, status=status.HTTP_400_BAD_REQUEST)

        # Check Redis cache first for recent messages
        cache_key = f"room:{chat_room_id}:messages:recent"
        cached_messages = None

        if not before_time:  # Only use cache for most recent messages
            cached_messages = cache.get(cache_key)

        if cached_messages and not before_time:
            logger.debug(f"Retrieved {len(cached_messages)} messages from cache")
            return Response({
                'messages': cached_messages[:limit],
                'source': 'cache',
                'count': len(cached_messages[:limit]),
                'has_more': len(cached_messages) >= limit
            })

        # Fetch from ScyllaDB
        try:
            messages = MessageScylla.get_messages_for_room(
                chat_room.id,
                limit=limit + 1,  # Fetch one extra to check if there are more
                before_time=before_time
            )

            messages_list = []
            for msg in messages[:limit]:  # Only return requested limit
                user_info = self._get_user_info(msg.user)
                messages_list.append({
                    'id': str(msg.id),
                    'content': msg.content,
                    'user': msg.user,
                    'user_info': user_info,
                    'created_at': msg.created_at.isoformat(),
                    'edited_at': msg.edited_at.isoformat() if msg.edited_at else None,
                    'reply_to': str(msg.reply_to) if msg.reply_to else None,
                    'media': msg.media
                })

            # Cache recent messages if this is the first page
            if not before_time and messages_list:
                cache.set(cache_key, messages_list, timeout=300)  # 5 minutes

            has_more = len(messages) > limit

            logger.debug(f"Retrieved {len(messages_list)} messages from ScyllaDB")
            return Response({
                'messages': messages_list,
                'source': 'database',
                'count': len(messages_list),
                'has_more': has_more,
                'next_cursor': messages_list[-1]['created_at'] if messages_list and has_more else None
            })

        except Exception as e:
            logger.error(f"Error fetching messages: {str(e)}")
            return Response(
                {"error": "Error fetching messages"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request, space_id, chat_room_id):
        """Create a new message with enhanced validation"""
        logger.debug(f"POST request to /chat/{space_id}/chat-rooms/{chat_room_id}/messages/")

        try:
            chat_room = ChatRoom.objects.get(id=chat_room_id, space__space_id=space_id)
        except ChatRoom.DoesNotExist:
            logger.error(f"Chat room {chat_room_id} not found for space {space_id}")
            return Response({"error": "Chat room not found"}, status=status.HTTP_404_NOT_FOUND)

        # Parse request data
        data = self._parse_request_data(request)
        if isinstance(data, Response):  # Error response
            return data

        # Validate message content
        content = data.get('content', '').strip()
        if not content and not data.get('media'):
            return Response(
                {"error": "Message must have content or media"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(content) > 2000:  # Message length limit
            return Response(
                {"error": "Message too long (max 2000 characters)"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Create message
            msg_id = uuid.uuid4()
            reply_to = data.get('reply_to')
            if reply_to:
                try:
                    reply_to = uuid.UUID(reply_to)
                except ValueError:
                    return Response(
                        {"error": "Invalid reply_to UUID"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            message = MessageScylla.create(
                id=msg_id,
                room=str(chat_room.id),
                user=str(request.user.user_id),
                content=content,
                created_at=timezone.now(),
                reply_to=reply_to,
                media=data.get('media', [])
            )

            # Prepare response
            user_info = self._get_user_info(str(request.user.user_id))
            response_data = {
                'id': str(message.id),
                'room': message.room,
                'user': message.user,
                'user_info': user_info,
                'content': message.content,
                'created_at': message.created_at.isoformat(),
                'reply_to': str(message.reply_to) if message.reply_to else None,
                'media': message.media
            }

            # Update caches
            self._update_caches(chat_room_id, response_data)

            logger.info(f"Message created: {msg_id} in room {chat_room_id}")
            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error creating message: {str(e)}")
            return Response(
                {"error": "Error creating message"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _parse_request_data(self, request):
        """Parse and validate request data"""
        if not request.data and request.body:
            try:
                return json.loads(request.body)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {str(e)}")
                return Response(
                    {"error": f"Invalid JSON: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return request.data

    def _get_user_info(self, user_id):
        """Get cached user information"""
        cache_key = f"user:{user_id}:info"
        user_info = cache.get(cache_key)

        if not user_info:
            try:
                user = User.objects.get(user_id=user_id)
                user_info = {
                    'user_id': str(user.user_id),
                    'email': getattr(user, 'email', 'Unknown'),
                    'display_name': f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip() or getattr(
                        user, 'email', 'Unknown')
                }
                cache.set(cache_key, user_info, timeout=3600)  # 1 hour
            except User.DoesNotExist:
                user_info = {
                    'user_id': user_id,
                    'email': 'Unknown User',
                    'display_name': 'Unknown User'
                }

        return user_info

    def _update_caches(self, chat_room_id, message_data):
        """Update various caches after message creation"""
        # Update Redis real-time features
        redis_chat_service.cache_message(chat_room_id, message_data)
        redis_chat_service.increment_message_count(chat_room_id)

        # Invalidate recent messages cache
        cache_key = f"room:{chat_room_id}:messages:recent"
        cache.delete(cache_key)



class ChatHealthView(APIView):
    """
    Health check endpoint for chat system
    """
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        redis_health = redis_chat_service.health_check()
        return Response({
            'status': 'healthy' if redis_health['status'] == 'healthy' else 'degraded',
            'redis': redis_health,
            'timestamp': datetime.now().isoformat()
        })

class RoomStatsView(APIView):
    """
    Get detailed statistics for a chat room
    """
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated, IsChatRoomMember]

    def get(self, request, space_id, chat_room_id):
        try:
            chat_room = ChatRoom.objects.get(id=chat_room_id, space__space_id=space_id)
        except ChatRoom.DoesNotExist:
            return Response({"error": "Chat room not found"}, status=status.HTTP_404_NOT_FOUND)

        stats = redis_chat_service.get_room_stats(chat_room_id)
        online_users = redis_chat_service.get_online_users(chat_room_id)
        typing_users = redis_chat_service.get_typing_users(chat_room_id)
        return Response({
            'room_id': chat_room_id,
            'stats': stats,
            'online_users': online_users,
            'typing_users': typing_users,
            'timestamp': datetime.now().isoformat()
        })