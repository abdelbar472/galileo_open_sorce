# chat/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from space.models import Space
from teams.models import Team
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Space)
def create_space_chat_room(sender, instance, created, **kwargs):
    """
    Create a default chat room when a space is created.
    """
    if created:
        try:
            # Import here to avoid circular imports
            from chat.models import ChatRoom

            ChatRoom.objects.create(
                name=f"{instance.name} General Chat",
                space=instance
            )
            logger.info(f"Default chat room created for space {instance.space_id}")
        except Exception as e:
            logger.error(f"Failed to create default chat room for space {instance.space_id}: {str(e)}")

@receiver(post_save, sender=Team)
def create_team_chat_room(sender, instance, created, **kwargs):
    """
    Create a default chat room when a team is created.
    """
    if created and instance.space:
        try:
            # Import here to avoid circular imports
            from chat.models import ChatRoom

            ChatRoom.objects.create(
                name=f"{instance.name} Team Chat",
                space=instance.space,
                team=instance
            )
            logger.info(f"Default chat room created for team {instance.id}")
        except Exception as e:
            logger.error(f"Failed to create default chat room for team {instance.id}: {str(e)}")