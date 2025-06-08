# chat/consumers.py - WebSocket consumer for real-time chat
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from .models import ChatRoom, ChatRoomMembership
from .services.redis_service import redis_chat_service

logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.room_id = None
        self.room_group_name = None
        self.user = None

    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope['user']

        # Check authentication
        if isinstance(self.user, AnonymousUser):
            logger.warning(f"Unauthenticated user attempted to connect to room {self.room_id}")
            await self.close()
            return

        # Check room membership
        has_access = await self.check_room_access(self.user, self.room_id)
        if not has_access:
            logger.warning(f"User {self.user.user_id} denied access to room {self.room_id}")
            await self.close()
            return

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        # Mark user as online
        await self.set_user_online()

        # Accept WebSocket connection
        await self.accept()

        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'room_id': self.room_id,
            'user_id': str(self.user.user_id)
        }))

        # Broadcast user joined
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_joined',
                'user_id': str(self.user.user_id),
                'user_info': await self.get_user_info(self.user)
            }
        )

        logger.info(f"User {self.user.user_id} connected to room {self.room_id}")

    async def disconnect(self, close_code):
        if self.room_group_name and self.user:
            # Mark user as offline
            await self.set_user_offline()

            # Leave room group
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

            # Broadcast user left
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_left',
                    'user_id': str(self.user.user_id)
                }
            )

            logger.info(f"User {self.user.user_id} disconnected from room {self.room_id}")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'typing_start':
                await self.handle_typing_start()
            elif message_type == 'typing_stop':
                await self.handle_typing_stop()
            elif message_type == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
            else:
                logger.warning(f"Unknown message type: {message_type}")

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received from user {self.user.user_id}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
        except Exception as e:
            logger.error(f"Error processing message from user {self.user.user_id}: {str(e)}")

    async def handle_typing_start(self):
        """Handle user starting to type"""
        await self.set_user_typing(True)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user_id': str(self.user.user_id),
                'user_info': await self.get_user_info(self.user),
                'is_typing': True
            }
        )

    async def handle_typing_stop(self):
        """Handle user stopping typing"""
        await self.set_user_typing(False)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user_id': str(self.user.user_id),
                'is_typing': False
            }
        )

    # WebSocket message handlers
    async def new_message(self, event):
        """Send new message to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'new_message',
            'message': event['message']
        }))

    async def message_updated(self, event):
        """Send message update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'message_updated',
            'message': event['message']
        }))

    async def message_deleted(self, event):
        """Send message deletion to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'message_deleted',
            'message_id': event['message_id']
        }))

    async def user_joined(self, event):
        """Send user joined notification"""
        if event['user_id'] != str(self.user.user_id):  # Don't send to self
            await self.send(text_data=json.dumps({
                'type': 'user_joined',
                'user_id': event['user_id'],
                'user_info': event['user_info']
            }))

    async def user_left(self, event):
        """Send user left notification"""
        if event['user_id'] != str(self.user.user_id):  # Don't send to self
            await self.send(text_data=json.dumps({
                'type': 'user_left',
                'user_id': event['user_id']
            }))

    async def typing_indicator(self, event):
        """Send typing indicator"""
        if event['user_id'] != str(self.user.user_id):  # Don't send to self
            await self.send(text_data=json.dumps({
                'type': 'typing_indicator',
                'user_id': event['user_id'],
                'user_info': event.get('user_info'),
                'is_typing': event['is_typing']
            }))

    # Helper methods
    @database_sync_to_async
    def check_room_access(self, user, room_id):
        """Check if user has access to the chat room"""
        try:
            ChatRoomMembership.objects.get(
                chat_room__id=room_id,
                user=user
            )
            return True
        except ChatRoomMembership.DoesNotExist:
            return False

    @database_sync_to_async
    def get_user_info(self, user):
        """Get user information for broadcasting"""
        return {
            'user_id': str(user.user_id),
            'email': getattr(user, 'email', 'Unknown'),
            'display_name': f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip() or getattr(user, 'email', 'Unknown')
        }

    async def set_user_online(self):
        """Mark user as online in Redis"""
        try:
            redis_chat_service.set_user_online(self.room_id, str(self.user.user_id))
        except Exception as e:
            logger.error(f"Error setting user online: {str(e)}")

    async def set_user_offline(self):
        """Mark user as offline in Redis"""
        try:
            redis_chat_service.set_user_offline(self.room_id, str(self.user.user_id))
        except Exception as e:
            logger.error(f"Error setting user offline: {str(e)}")

    async def set_user_typing(self, is_typing):
        """Set user typing status in Redis"""
        try:
            if is_typing:
                redis_chat_service.set_user_typing(self.room_id, str(self.user.user_id))
            else:
                redis_chat_service.unset_user_typing(self.room_id, str(self.user.user_id))
        except Exception as e:
            logger.error(f"Error setting typing status: {str(e)}")