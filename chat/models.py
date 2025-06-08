# chat/models.py
import uuid
from django.db import models
from django.conf import settings
from cassandra.cqlengine import columns
from cassandra.cqlengine.models import Model
from space.models import Space
from teams.models import Team

class ChatRoom(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name='chat_rooms')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='chat_rooms', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.space.name})"

class ChatRoomMembership(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chat_room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_admin = models.BooleanField(default=False)

    class Meta:
        unique_together = ('chat_room', 'user')

# ScyllaDB model for storing messages
class MessageScylla(Model):
    __keyspace__ = 'galileo'

    # Optimized primary key structure for better query performance
    room = columns.Text(partition_key=True)  # Partition key - distributes data
    created_at = columns.DateTime(primary_key=True, clustering_order="DESC")  # Clustering key for time ordering
    id = columns.UUID(primary_key=True, default=uuid.uuid4)  # Secondary clustering key for uniqueness

    # Data fields
    user = columns.Text()  # User ID as string
    content = columns.Text()  # Message content
    media = columns.List(columns.Text, default=list)  # Media attachments
    edited_at = columns.DateTime()  # Track message edits
    reply_to = columns.UUID()  # For threaded conversations

    class Meta:
        get_pk_field = 'room'  # Primary partition key

    @classmethod
    def get_messages_for_room(cls, room_id, limit=50, before_time=None):
        """Optimized query method for retrieving messages"""
        query = cls.objects.filter(room=str(room_id))

        if before_time:
            query = query.filter(created_at__lt=before_time)

        return query.limit(limit).all()