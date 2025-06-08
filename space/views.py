from rest_framework import viewsets, status, permissions, generics
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from .models import *
from .serializers import *
from .permissions import *
from .authentication import SpaceJWTAuthentication
from django.utils import timezone
from rest_framework import exceptions
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import AccessToken
import random
import string
import logging
from datetime import timedelta
from outh.models import User  # Fix 'outh' to 'auth'
logger = logging.getLogger(__name__)
    
    
    
class CreateSpaceView(generics.CreateAPIView):
        """
        API endpoint to create a space and list spaces for the authenticated user.
        """
        queryset = Space.objects.all()
        serializer_class = SpaceSerializer
        authentication_classes = [JWTAuthentication, SessionAuthentication]
        permission_classes = [permissions.IsAuthenticated]
        pagination_class = PageNumberPagination
    
        def post(self, request):
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                space = serializer.save(created_by=self.request.user)
                logger.info(f"Space created: {space.space_id} by user {request.user.user_id} at {timezone.now()}")
                SpaceMembership.objects.create(
                    user=self.request.user,
                    space=serializer.instance,
                    role='manager',
                    is_admin=True
                )
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            logger.error(f"Space creation failed: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
        def get(self, request):
            memberships = SpaceMembership.objects.filter(user=request.user).values_list('space_id', flat=True)
            spaces = Space.objects.filter(space_id__in=memberships)
            if not spaces.exists():
                return Response({"message": "No spaces found for this user"}, status=status.HTTP_200_OK)
    
            serializer = SpaceSerializer(spaces, many=True, context={'request': request})
            page = self.paginate_queryset(serializer.data)
            if page is not None:
                return self.get_paginated_response(page)
            return Response(serializer.data, status=status.HTTP_200_OK)
    
class SpaceDetailView(generics.RetrieveAPIView):
        """
        API endpoint to retrieve details of a specific space.
        """
        queryset = Space.objects.all()
        serializer_class = SpaceSerializer
        authentication_classes = [SessionAuthentication, JWTAuthentication, SpaceJWTAuthentication]
        permission_classes = [permissions.IsAuthenticated, IsSpaceOwnerOrAdmin]
        lookup_field = 'space_id'
    
        def get(self, request, *args, **kwargs):
            space = self.get_object()
            serializer = self.get_serializer(space, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
    
class SpaceJWTView(generics.GenericAPIView):
        """
        API endpoint to issue a custom space-specific JWT for the authenticated user.
        Supports custom lifetime (1-30 days) and scope (read, write, admin).
        Issued as of 01:34 AM EEST, Saturday, May 17, 2025.
        """
        authentication_classes = [SessionAuthentication, JWTAuthentication, SpaceJWTAuthentication]
        permission_classes = [permissions.IsAuthenticated, IsSpaceOwnerOrAdmin]
        serializer_class = SpaceJWTSerializer
    
        def get(self, request, space_id):  # Update to space_id for consistency
            logger.warning(f"GET method not supported for /space-jwt/ at {timezone.now()}")
            return Response(
                {"error": "Method 'GET' not allowed. Use POST to issue a Space JWT."},
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )
    
        def post(self, request, space_id):  # Change space_pk to space_id
            serializer = self.get_serializer(data=request.data)
            if not serializer.is_valid():
                logger.error(f"Invalid data for SpaceJWT: {serializer.errors} at {timezone.now()}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            try:
                space = Space.objects.get(space_id=space_id)
            except Space.DoesNotExist:
                logger.error(f"Space not found: {space_id} at {timezone.now()}")
                return Response({"error": "Space not found"}, status=status.HTTP_404_NOT_FOUND)
    
            try:
                membership = SpaceMembership.objects.get(space=space, user=request.user)
            except SpaceMembership.DoesNotExist:
                logger.error(f"No membership found for user {request.user.user_id} in space {space_id} at {timezone.now()}")
                return Response({"error": "User is not a member of this space"}, status=status.HTTP_403_FORBIDDEN)
    
            lifetime_days = serializer.validated_data['lifetime_days']
            scope = serializer.validated_data['scope']
    
            if scope == 'admin' and not (membership.is_admin or space.created_by == request.user):
                logger.warning(f"User {request.user.user_id} attempted to request admin scope without permission at {timezone.now()}")
                return Response({"error": "Admin scope requires admin privileges."}, status=status.HTTP_403_FORBIDDEN)
    
            space_token = AccessToken()
            space_token['user_id'] = str(request.user.user_id)
            space_token['space_id'] = str(space.space_id)
            space_token['role'] = membership.role
            space_token['is_admin'] = membership.is_admin
            space_token['scope'] = scope
            space_token['token_type'] = 'space_jwt'
            space_token['iat'] = timezone.now().timestamp()
            space_token.set_exp(lifetime=timedelta(days=lifetime_days))
    
            logger.info(f"Space JWT issued for user {request.user.user_id} in space {space_id} with scope {scope} at {timezone.now()}")
            return Response({
                "space_jwt": str(space_token),
                "expires_in": lifetime_days * 86400,
                "scope": scope,
                "issued_at": timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
    
    
class SpaceAccessTokenView(generics.GenericAPIView):
        """
        API endpoint to manage space access tokens.
        GET: List all tokens for a space (admin only)
        POST: Generate a new token for a space
        """
        authentication_classes = [SessionAuthentication, JWTAuthentication, SpaceJWTAuthentication]
        permission_classes = [permissions.IsAuthenticated, IsSpaceOwnerOrAdmin]
        serializer_class = SpaceTokenSerializer  # Add this line
    
    
        def get(self, request, space_id):
            """List all access tokens for a space"""
            try:
                space = Space.objects.get(space_id=space_id)
            except Space.DoesNotExist:
                logger.error(f"Space not found: {space_id} at {timezone.now()}")
                return Response({"error": "Space not found"}, status=status.HTTP_404_NOT_FOUND)
    
            # Check if the requesting user is an admin
            try:
                requester_membership = SpaceMembership.objects.get(space=space, user=request.user)
                if not requester_membership.is_admin:
                    logger.warning(
                        f"User {request.user.user_id} attempted to view tokens without admin privileges at {timezone.now()}")
                    return Response({"error": "Only admins can view space tokens"}, status=status.HTTP_403_FORBIDDEN)
            except SpaceMembership.DoesNotExist:
                logger.error(f"User {request.user.user_id} is not a member of space {space_id} at {timezone.now()}")
                return Response({"error": "You are not a member of this space"}, status=status.HTTP_403_FORBIDDEN)
    
            # Get all space tokens (implementation depends on how you store tokens)
            # This is a placeholder - you'll need to implement based on your token storage
            from rest_framework_simplejwt.tokens import AccessToken
            from django.conf import settings
    
            # You might have a model like SpaceToken to store tokens
            # tokens = SpaceToken.objects.filter(space=space)
    
            # For demo purposes, generate a sample token
            token = AccessToken()
            token.payload.update({
                'token_type': 'space_jwt',
                'user_id': str(request.user.user_id),
                'space_id': str(space.space_id),
                'scope': 'read write',
                'exp': timezone.now() + timezone.timedelta(days=30)
            })
    
            logger.info(f"Space tokens accessed for space {space_id} by user {request.user.user_id} at {timezone.now()}")
            return Response({
                'space_id': space.space_id,
                'space_name': space.name,
                'tokens': [{
                    'token': str(token),
                    'expires_at': (timezone.now() + timezone.timedelta(days=30)).isoformat(),
                    'scope': 'read write'
                }]
            }, status=status.HTTP_200_OK)
    
        def post(self, request, space_id):
            """Generate a new token for a space"""
            try:
                space = Space.objects.get(space_id=space_id)
            except Space.DoesNotExist:
                logger.error(f"Space not found: {space_id} at {timezone.now()}")
                return Response({"error": "Space not found"}, status=status.HTTP_404_NOT_FOUND)
    
            # Check if the requesting user is an admin
            try:
                requester_membership = SpaceMembership.objects.get(space=space, user=request.user)
                if not requester_membership.is_admin:
                    logger.warning(
                        f"User {request.user.user_id} attempted to generate token without admin privileges at {timezone.now()}")
                    return Response({"error": "Only admins can generate space tokens"}, status=status.HTTP_403_FORBIDDEN)
            except SpaceMembership.DoesNotExist:
                logger.error(f"User {request.user.user_id} is not a member of space {space_id} at {timezone.now()}")
                return Response({"error": "You are not a member of this space"}, status=status.HTTP_403_FORBIDDEN)
    
            # Get scope from request or use default
            scope = request.data.get('scope', 'read write')
            expiry_days = request.data.get('expiry_days', 30)
    
            # Generate a new token
            from rest_framework_simplejwt.tokens import AccessToken
            token = AccessToken()
            token.payload.update({
                'token_type': 'space_jwt',
                'user_id': str(request.user.user_id),
                'space_id': str(space.space_id),
                'scope': scope,
                'exp': timezone.now() + timezone.timedelta(days=expiry_days)
            })
    
            # In a real implementation, you might save this token to a database
            # new_token = SpaceToken.objects.create(
            #     space=space,
            #     token=str(token),
            #     created_by=request.user,
            #     scope=scope,
            #     expires_at=timezone.now() + timezone.timedelta(days=expiry_days)
            # )
    
            logger.info(
                f"New space token generated for space {space_id} by user {request.user.user_id} at {timezone.now()}")
            return Response({
                'token': str(token),
                'expires_at': (timezone.now() + timezone.timedelta(days=expiry_days)).isoformat(),
                'scope': scope
            }, status=status.HTTP_201_CREATED)
    
class InviteView(generics.GenericAPIView):
        """
        API endpoint to generate and send an OTP for inviting a user to a space.
        """
        serializer_class = InviteSerializer
        authentication_classes = [SessionAuthentication, JWTAuthentication, SpaceJWTAuthentication]
        permission_classes = [permissions.IsAuthenticated, IsSpaceOwnerOrAdmin]
    
        def post(self, request, space_id):
            logger.debug(f"Received invite request for space_id: {space_id} by user: {request.user} at {timezone.now()}")
    
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                username = serializer.validated_data['username']
                role = serializer.validated_data['role']
    
                # Find user by username
                try:
                    user = User.objects.get(username=username)
                except User.DoesNotExist:
                    logger.error(f"User with username {username} not found at {timezone.now()}")
                    return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    
                try:
                    space = Space.objects.get(space_id=space_id)
                    logger.debug(f"Found space: {space.name} at {timezone.now()}")
                except Space.DoesNotExist:
                    logger.error(f"Space not found: {space_id} at {timezone.now()}")
                    return Response({"error": "Space not found"}, status=status.HTTP_404_NOT_FOUND)
    
                # Check if user is already a member
                if SpaceMembership.objects.filter(user=user, space=space).exists():
                    logger.warning(f"User {username} is already a member of space {space_id} at {timezone.now()}")
                    return Response({"error": "User is already a member of this space"}, status=status.HTTP_400_BAD_REQUEST)
    
                otp = ''.join(random.choice(string.digits) for _ in range(6))
                invitation = Invitation.objects.create(
                    space=space,
                    invited_user=user,  # Pass the User instance, not the username string
                    invited_role=role,
                    otp=otp,
                    otp_expiry=timezone.now() + timedelta(minutes=5)
                )
    
                send_mail(
                    subject='Invitation to Join Space',
                    message=f'You have been invited to join the space "{space.name}" as a {role}. Your OTP is {otp}, valid for 5 minutes. Space ID: {space_id}. Issued at {timezone.now().isoformat()}.',
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
    
                logger.info(f"OTP sent to user {username} for space {space_id} at {timezone.now()}")
                return Response({"message": "OTP sent to the user"}, status=status.HTTP_200_OK)
    
            logger.error(f"Invite failed: {serializer.errors} at {timezone.now()}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
        def get(self, request, space_id):
            logger.warning(f"GET method not supported for /invite/. Redirecting to login. at {timezone.now()}")
            return Response({"error": "Method 'GET' not allowed. Please log in and use POST to send an invitation.","redirect": "/login/"}, status=status.HTTP_401_UNAUTHORIZED)
    
class JoinView(generics.GenericAPIView):
        """
        API endpoint to join a space using an invitation link.
        """
        serializer_class = JoinSerializer
        authentication_classes = [JWTAuthentication, SessionAuthentication]
        permission_classes = [permissions.IsAuthenticated]
    
        def post(self, request):
            # Extract token and space_id from query parameters (for link-based joining)
            invitation_token = request.GET.get('token')
            space_id = request.GET.get('space_id')
    
            if not invitation_token or not space_id:
                # Fall back to serializer for POST body data if no query params
                serializer = self.get_serializer(data=request.data)
                if serializer.is_valid():
                    space = serializer.validated_data['space_id']
                    otp = serializer.validated_data['otp']
                    user = self.request.user
    
                    try:
                        invitation = Invitation.objects.get(
                            space=space,
                            invited_user=user,
                            otp=otp,
                            otp_expiry__gte=timezone.now()
                        )
                    except Invitation.DoesNotExist:
                        logger.error(f"Invalid or expired OTP for user {user.user_id} in space {space.space_id} at {timezone.now()}")
                        return Response({"error": "Invalid or expired OTP"}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            else:
                # Handle invitation link
                try:
                    space = Space.objects.get(space_id=space_id)
                    invitation = Invitation.objects.get(
                        space=space,
                        invitation_token=invitation_token,
                        otp_expiry__gte=timezone.now()
                    )
                except (Space.DoesNotExist, Invitation.DoesNotExist):
                    logger.error(f"Invalid or expired invitation token {invitation_token} for space {space_id} at {timezone.now()}")
                    return Response({"error": "Invalid or expired invitation link"}, status=status.HTTP_400_BAD_REQUEST)
    
                user = self.request.user
    
            if SpaceMembership.objects.filter(user=user, space=space).exists():
                logger.warning(f"User {user.user_id} is already a member of space {space.space_id} at {timezone.now()}")
                return Response({"error": "User is already a member of the space"}, status=status.HTTP_400_BAD_REQUEST)
    
            SpaceMembership.objects.create(
                user=user,
                space=space,
                role=invitation.invited_role,
                is_admin=invitation.invited_role == 'manager'
            )
            invitation.delete()
            logger.info(f"User {user.user_id} joined space {space.space_id} as {invitation.invited_role} at {timezone.now()}")
            return Response({"message": f"Successfully joined space as {invitation.invited_role}"}, status=status.HTTP_200_OK)

class RemoveSpaceMemberView(generics.GenericAPIView):
        """
        API endpoint to remove a member from a space by username.
        Only admins or managers can perform this action.
        """
        authentication_classes = [SessionAuthentication, JWTAuthentication, SpaceJWTAuthentication]
        permission_classes = [permissions.IsAuthenticated, IsSpaceOwnerOrAdmin]
        serializer_class = RemoveMemberSerializer  # Add serializer_class
    
        def get(self, request, space_id):
            """List all members of the space that can be selected for deletion."""
            try:
                space = Space.objects.get(space_id=space_id)
            except Space.DoesNotExist:
                logger.error(f"Space not found: {space_id} at {timezone.now()}")
                return Response({"error": "Space not found"}, status=status.HTTP_404_NOT_FOUND)
    
            # Check if the requesting user is an admin or manager
            try:
                requester_membership = SpaceMembership.objects.get(space=space, user=request.user)
                if not requester_membership.is_admin:
                    logger.warning(
                        f"User {request.user.user_id} attempted to list members without admin privileges at {timezone.now()}")
                    return Response({"error": "Only admins or managers can view this list."},
                                    status=status.HTTP_403_FORBIDDEN)
            except SpaceMembership.DoesNotExist:
                logger.error(f"User {request.user.user_id} is not a member of space {space_id} at {timezone.now()}")
                return Response({"error": "You are not a member of this space"}, status=status.HTTP_403_FORBIDDEN)
    
            # Get all members except the requesting user
            memberships = SpaceMembership.objects.filter(space=space).exclude(user=request.user)
    
            # Format the response data
            members_data = []
            for membership in memberships:
                members_data.append({
                    'username': membership.user.username,
                    'email': membership.user.email,
                    'role': membership.role,
                    'is_admin': membership.is_admin,
                    'joined_at': membership.created_at.isoformat() if hasattr(membership, 'created_at') else None
                })
    
            logger.info(f"Members list accessed for space {space_id} by user {request.user.user_id} at {timezone.now()}")
            return Response({
                'space_id': space.space_id,
                'space_name': space.name,
                'members': members_data
            }, status=status.HTTP_200_OK)
    
        def post(self, request, space_id):
            try:
                space = Space.objects.get(space_id=space_id)
            except Space.DoesNotExist:
                logger.error(f"Space not found: {space_id} at {timezone.now()}")
                return Response({"error": "Space not found"}, status=status.HTTP_404_NOT_FOUND)
    
            # Check if the requesting user is an admin or manager
            try:
                requester_membership = SpaceMembership.objects.get(space=space, user=request.user)
                if not requester_membership.is_admin:
                    logger.warning(
                        f"User {request.user.user_id} attempted to remove a member without admin privileges at {timezone.now()}")
                    return Response({"error": "Only admins or managers can remove members."},
                                    status=status.HTTP_403_FORBIDDEN)
            except SpaceMembership.DoesNotExist:
                logger.error(f"User {request.user.user_id} is not a member of space {space_id} at {timezone.now()}")
                return Response({"error": "You are not a member of this space"}, status=status.HTTP_403_FORBIDDEN)
    
            # Validate input using the serializer
            serializer = self.get_serializer(data=request.data)
            if not serializer.is_valid():
                logger.error(f"Invalid data for member removal: {serializer.errors} at {timezone.now()}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
            # Get the validated username
            user_to_remove = serializer.validated_data['username']
    
            try:
                membership_to_remove = SpaceMembership.objects.get(space=space, user=user_to_remove)
            except SpaceMembership.DoesNotExist:
                logger.error(f"User {user_to_remove.username} is not a member of space {space_id} at {timezone.now()}")
                return Response({"error": "User is not a member of this space"}, status=status.HTTP_404_NOT_FOUND)
    
            # Prevent the admin from removing themselves
            if membership_to_remove.user == request.user:
                logger.warning(
                    f"User {request.user.user_id} attempted to remove themselves from space {space_id} at {timezone.now()}")
                return Response({"error": "You cannot remove yourself as an admin or manager."},
                                status=status.HTTP_400_BAD_REQUEST)
    
            # Remove the member
            membership_to_remove.delete()
            logger.info(
                f"User {user_to_remove.username} removed from space {space_id} by user {request.user.user_id} at {timezone.now()}")
            return Response({"message": f"User {user_to_remove.username} removed from the space."},
                            status=status.HTTP_200_OK)
    
    
class ChangeSpaceMemberRoleView(generics.GenericAPIView):
        """
        API endpoint to change a member's role in a space. Only admins or managers can perform this action.
        """
        authentication_classes = [SessionAuthentication, JWTAuthentication, SpaceJWTAuthentication]
        permission_classes = [permissions.IsAuthenticated, IsSpaceOwnerOrAdmin]
        serializer_class = ChangeRoleSerializer
    
        def get(self, request, space_id):
            """
            Handle GET requests by returning an error, as this endpoint only supports PATCH.
            """
            logger.warning(f"GET method not supported for /change-role/ at {timezone.now()}")
            return Response(
                {"error": "Method 'GET' not allowed. Use PATCH to change a member's role."},
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )
    
        def patch(self, request, space_id):
            try:
                space = Space.objects.get(space_id=space_id)
            except Space.DoesNotExist:
                logger.error(f"Space not found: {space_id} at {timezone.now()}")
                return Response({"error": "Space not found"}, status=status.HTTP_404_NOT_FOUND)
    
            # Check if the requesting user is an admin or manager
            try:
                requester_membership = SpaceMembership.objects.get(space=space, user=request.user)
                if not requester_membership.is_admin:
                    logger.warning(
                        f"User {request.user.user_id} attempted to change a role without admin privileges at {timezone.now()}")
                    return Response({"error": "Only admins or managers can change roles."},
                                    status=status.HTTP_403_FORBIDDEN)
            except SpaceMembership.DoesNotExist:
                logger.error(f"User {request.user.user_id} is not a member of space {space_id} at {timezone.now()}")
                return Response({"error": "You are not a member of this space"}, status=status.HTTP_403_FORBIDDEN)
    
            # Get the username from request data
            username = request.data.get('username')
            if not username:
                return Response({"error": "username is required"}, status=status.HTTP_400_BAD_REQUEST)
    
            new_role = request.data.get('role')
            if not new_role:
                return Response({"error": "role is required"}, status=status.HTTP_400_BAD_REQUEST)
    
            if new_role not in ['member', 'guest', 'manager']:
                return Response({"error": "Invalid role. Must be one of: member, guest, manager"},
                                status=status.HTTP_400_BAD_REQUEST)
    
            try:
                user_to_update = User.objects.get(username=username)
            except User.DoesNotExist:
                logger.error(f"User with username {username} not found at {timezone.now()}")
                return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    
            try:
                membership_to_update = SpaceMembership.objects.get(space=space, user=user_to_update)
            except SpaceMembership.DoesNotExist:
                logger.error(f"User {username} is not a member of space {space_id} at {timezone.now()}")
                return Response({"error": "User is not a member of this space"}, status=status.HTTP_404_NOT_FOUND)
    
            # Prevent the admin from changing their own role
            if membership_to_update.user == request.user:
                logger.warning(
                    f"User {request.user.user_id} attempted to change their own role in space {space_id} at {timezone.now()}")
                return Response({"error": "You cannot change your own role."}, status=status.HTTP_400_BAD_REQUEST)
    
            # Update the role and is_admin status
            old_role = membership_to_update.role
            membership_to_update.role = new_role
            membership_to_update.is_admin = (new_role == 'manager')
            membership_to_update.save()
    
            logger.info(
                f"User {username}'s role changed from {old_role} to {new_role} in space {space_id} by user {request.user.user_id} at {timezone.now()}")
            return Response({"message": f"User {username}'s role changed to {new_role}."}, status=status.HTTP_200_OK)

class LeaveSpaceView(generics.GenericAPIView):
    """
    API endpoint for a user to leave a space they are a member of.
    """
    authentication_classes = [SessionAuthentication, JWTAuthentication, SpaceJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]  # Removed IsSpaceOwnerOrAdmin
    serializer_class = serializers.Serializer  # Empty serializer since we don't need input data

    def post(self, request, space_id):
        try:
            space = Space.objects.get(space_id=space_id)
        except Space.DoesNotExist:
            logger.error(f"Space not found: {space_id} at {timezone.now()}")
            return Response({"error": "Space not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            membership = SpaceMembership.objects.get(space=space, user=request.user)
        except SpaceMembership.DoesNotExist:
            logger.error(f"User {request.user.user_id} is not a member of space {space_id} at {timezone.now()}")
            return Response({"error": "You are not a member of this space"}, status=status.HTTP_404_NOT_FOUND)

        # Check if user is the only admin
        admin_count = SpaceMembership.objects.filter(space=space, is_admin=True).count()
        if membership.is_admin and admin_count == 1:
            logger.warning(
                f"User {request.user.user_id} attempted to leave space {space_id} as the only admin at {timezone.now()}")
            return Response(
                {"error": "You are the only admin. Please assign another admin before leaving."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get all admin emails for notification
        admin_emails = SpaceMembership.objects.filter(
            space=space,
            is_admin=True
        ).exclude(
            user=request.user
        ).values_list('user__email', flat=True)

        # Send notification to admins
        if admin_emails:
            try:
                send_mail(
                    subject=f'User Left Space: {space.name}',
                    message=f'User {request.user.username} has left the space "{space.name}" at {timezone.now().isoformat()}.',
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=list(admin_emails),
                    fail_silently=True,
                )
                logger.info(
                    f"Notification email sent to admins about user {request.user.username} leaving space {space.name}")
            except Exception as e:
                logger.error(f"Failed to send email notification: {str(e)}")

        # Delete the membership
        membership.delete()
        logger.info(f"User {request.user.user_id} left space {space_id} at {timezone.now()}")
        return Response({"message": "You have successfully left the space"}, status=status.HTTP_200_OK)

    def get(self, request, space_id):
        """Allow GET requests to show confirmation page"""
        try:
            space = Space.objects.get(space_id=space_id)
        except Space.DoesNotExist:
            logger.error(f"Space not found: {space_id} at {timezone.now()}")
            return Response({"error": "Space not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            membership = SpaceMembership.objects.get(space=space, user=request.user)
            return Response({
                "space_id": space_id,
                "space_name": space.name,
                "user_role": membership.role,
                "message": "Are you sure you want to leave this space? Submit a POST request to confirm."
            }, status=status.HTTP_200_OK)
        except SpaceMembership.DoesNotExist:
            return Response({"error": "You are not a member of this space"}, status=status.HTTP_404_NOT_FOUND)