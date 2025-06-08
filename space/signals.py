# signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
import logging
from .models import Space, SpaceMembership, Invitation
from teams.models import Team, Member
from outh.models import User
from chat.models import ChatRoom
from workspace.models import Workspace

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Space)
def space_created_or_updated(sender, instance, created, **kwargs):
    """
    Handle the creation or update of a Space model instance.
    - On creation: Logs the event and sends a notification email to the creator.
    - On update: Logs the update event.
    """
    if created:
        logger.info(f"Space {instance.name} (ID: {instance.space_id}) created by {instance.created_by.user_id}")
        try:
            # Create default team for the space
            create_default_team(sender, instance, created, **kwargs)

            # Create default chat room for the space
            create_default_chat_room(instance)

            send_mail(
                subject=f"New Space Created: {instance.name}",
                message=f"Dear {instance.created_by.username},\n\nYou have successfully created the space '{instance.name}'.\n\nBest regards,\nYour App Team",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[instance.created_by.email],
                fail_silently=False,
            )
            logger.debug(f"Notification email sent to {instance.created_by.email} for space {instance.space_id}")
        except Exception as e:
            logger.error(f"Failed to send email for space creation {instance.space_id}: {str(e)}")
    else:
        logger.info(f"Space {instance.name} (ID: {instance.space_id}) updated")


def create_default_team(sender, instance, created, **kwargs):
    """
    Create a default team with the same name as the space when a space is created.
    """
    if created:
        # Create a team with the same name as space
        team = Team.objects.create(
            name=instance.name,
            description=f"Default team for {instance.name} space",
            space=instance
        )

        # Add space creator as team manager
        Member.objects.create(
            user=instance.created_by,
            team=team,
            role='manager',
            is_admin=True
        )

        logger.info(f"Default team '{team.name}' created for space {instance.space_id}")


def create_default_chat_room(instance):
    """
    Create a default chat room for a space.
    """
    try:
        ChatRoom.objects.create(
            name=f"{instance.name} General Chat",
            space=instance
        )
        logger.info(f"Default chat room created for space {instance.space_id}")
    except Exception as e:
        logger.error(f"Failed to create default chat room for space {instance.space_id}: {str(e)}")


@receiver(post_save, sender=SpaceMembership)
def space_membership_created(sender, instance, created, **kwargs):
    """
    Handle the creation of a SpaceMembership model instance.
    - Logs the event when a user joins a space.
    - Sends a welcome email to the new member.
    - Adds the member to the default team in the space.
    """
    if created:
        space = instance.space
        logger.info(f"User {instance.user.user_id} joined space {space.name} (ID: {space.space_id}) as {instance.role}")

        # Add user to the default team (assuming the first team is the default)
        try:
            default_team = Team.objects.filter(space=space).first()
            if default_team:
                # Check if not already a member
                if not Member.objects.filter(user=instance.user, team=default_team).exists():
                    # Map space role to team role
                    team_role = instance.role
                    is_admin = instance.is_admin

                    Member.objects.create(
                        user=instance.user,
                        team=default_team,
                        role=team_role,
                        is_admin=is_admin
                    )
                    logger.info(
                        f"User {instance.user.user_id} added to team {default_team.name} (ID: {default_team.id}) as {team_role}")
        except Exception as e:
            logger.error(f"Failed to add user to default team: {str(e)}")

        try:
            send_mail(
                subject=f"Welcome to Space {space.name}",
                message=f"Dear {instance.user.username},\n\nYou have been added to the space '{space.name}' with the role '{instance.role}'.\n\nBest regards,\nYour App Team",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[instance.user.email],
                fail_silently=False,
            )
            logger.debug(f"Welcome email sent to {instance.user.email} for space {space.space_id}")
        except Exception as e:
            logger.error(f"Failed to send welcome email for space membership {space.space_id}: {str(e)}")


@receiver(post_delete, sender=SpaceMembership)
def space_membership_deleted(sender, instance, **kwargs):
    """
    Handle the deletion of a SpaceMembership model instance.
    - Logs the event when a user is removed from a space.
    - Removes the user from all teams in the space.
    - Sends a notification email to the removed member.
    """
    space = instance.space
    logger.info(f"User {instance.user.user_id} removed from space {space.name} (ID: {space.space_id})")

    # Remove user from all teams in the space
    try:
        teams_in_space = Team.objects.filter(space=space)
        member_records = Member.objects.filter(team__in=teams_in_space, user=instance.user)
        member_count = member_records.count()
        member_records.delete()
        logger.info(f"User {instance.user.user_id} removed from {member_count} teams in space {space.space_id}")
    except Exception as e:
        logger.error(f"Failed to remove user from teams in space {space.space_id}: {str(e)}")

    try:
        send_mail(
            subject=f"Removed from Space {space.name}",
            message=f"Dear {instance.user.username},\n\nYou have been removed from the space '{space.name}'.\n\nBest regards,\nYour App Team",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[instance.user.email],
            fail_silently=False,
        )
        logger.debug(f"Removal email sent to {instance.user.email} for space {space.space_id}")
    except Exception as e:
        logger.error(f"Failed to send removal email for space {space.space_id}: {str(e)}")


@receiver(post_save, sender=Invitation)
def invitation_created(sender, instance, created, **kwargs):
    """
    Handle the creation of an Invitation model instance.
    - Logs the event when an invitation is created.
    - Sends an email with the OTP to the invited user, if the user exists.
    """
    if created:
        space = instance.space
        user = instance.invited_user
        if user is None:
            logger.warning(
                f"Invitation created for space {space.name} (ID: {space.space_id}) as {instance.invited_role} without an invited user")
            return
        logger.info(
            f"Invitation created for user {user.user_id} to join space {space.name} (ID: {space.space_id}) as {instance.invited_role}")
        try:
            send_mail(
                subject=f"Invitation to Join Space {space.name}",
                message=f"Dear {user.username},\n\nYou have been invited to join the space '{space.name}' as a {instance.invited_role}. Your OTP is {instance.otp}, valid until {instance.otp_expiry.isoformat()}.\n\nBest regards,\nYour App Team",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user.email],
                fail_silently=False,
            )
            logger.debug(f"Invitation email sent to {user.email} for space {space.space_id}")
        except Exception as e:
            logger.error(f"Failed to send invitation email for space {space.space_id}: {str(e)}")


@receiver(post_save, sender=Team)
def team_created_or_updated(sender, instance, created, **kwargs):
    """
    Handle the creation or update of a Team model instance.
    - On creation: Logs the event and sends a notification email to the creator (first admin member).
    - On update: Logs the update event.
    """
    if created:
        creator = instance.members.filter(is_admin=True).first()
        if creator:
            logger.info(
                f"Team {instance.name} (ID: {instance.id}) created in space {instance.space.space_id} by {creator.user.user_id}")
            try:
                send_mail(
                    subject=f"New Team Created: {instance.name}",
                    message=f"Dear {creator.user.username},\n\nYou have successfully created the team '{instance.name}' in space '{instance.space.name}'.\n\nBest regards,\nYour App Team",
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[creator.user.email],
                    fail_silently=False,
                )
                logger.debug(f"Notification email sent to {creator.user.email} for team {instance.id}")
            except Exception as e:
                logger.error(f"Failed to send email for team creation {instance.id}: {str(e)}")
        else:
            logger.warning(f"Team {instance.name} (ID: {instance.id}) created without an admin member")
    else:
        logger.info(f"Team {instance.name} (ID: {instance.id}) updated")


@receiver(post_save, sender=Member)
def team_membership_created(sender, instance, created, **kwargs):
    """
    Handle the creation of a Member (team membership) model instance.
    - Logs the event when a user joins a team.
    - Sends a welcome email to the new team member.
    """
    if created:
        team = instance.team
        logger.info(f"User {instance.user.user_id} joined team {team.name} (ID: {team.id}) as {instance.role}")
        try:
            send_mail(
                subject=f"Welcome to Team {team.name}",
                message=f"Dear {instance.user.username},\n\nYou have been added to the team '{team.name}' in space '{team.space.name}' with the role '{instance.role}'.\n\nBest regards,\nYour App Team",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[instance.user.email],
                fail_silently=False,
            )
            logger.debug(f"Welcome email sent to {instance.user.email} for team {team.id}")
        except Exception as e:
            logger.error(f"Failed to send welcome email for team membership {team.id}: {str(e)}")


@receiver(post_delete, sender=Member)
def team_membership_deleted(sender, instance, **kwargs):
    """
    Handle the deletion of a Member (team membership) model instance.
    - Logs the event when a user is removed from a team.
    - Sends a notification email to the removed member.
    """
    team = instance.team
    logger.info(f"User {instance.user.user_id} removed from team {team.name} (ID: {team.id})")
    try:
        send_mail(
            subject=f"Removed from Team {team.name}",
            message=f"Dear {instance.user.username},\n\nYou have been removed from the team '{team.name}' in space '{team.space.name}'.\n\nBest regards,\nYour App Team",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[instance.user.email],
            fail_silently=False,
        )
        logger.debug(f"Removal email sent to {instance.user.email} for team {team.id}")
    except Exception as e:
        logger.error(f"Failed to send removal email for team {team.id}: {str(e)}")

@receiver(post_save, sender=Workspace)
def workspace_created(sender, instance, created, **kwargs):
    if created:
        Task.objects.create(
            workspace=instance,
            title="Welcome Task",
            description="Explore your new workspace to-do list!"
        )
        logger.info(f"Default task created for workspace {instance.name}")