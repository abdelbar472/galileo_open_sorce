# post/views.py
from datetime import timedelta
from rest_framework import generics, status
from rest_framework.response import Response
from .models import *
from .serializers import *
from .permissions import *
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from space.models import Space, SpaceMembership
from space.authentication import SpaceJWTAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
import logging

logger = logging.getLogger(__name__)

class CreatePostView(generics.CreateAPIView):
    serializer_class = PostCreateSerializer
    authentication_classes = [SessionAuthentication, JWTAuthentication, SpaceJWTAuthentication]
    permission_classes = [PostPermissions, IsAuthenticated]

    def post(self, request, *args, **kwargs):
        space_id = kwargs.get('space_id')
        try:
            space = Space.objects.get(space_id=space_id)
        except Space.DoesNotExist:
            logger.error(f"Space {space_id} not found at {timezone.now()}")
            return Response({"error": "Space not found"}, status=status.HTTP_404_NOT_FOUND)

        # Check space membership
        if not SpaceMembership.objects.filter(user=request.user, space=space).exists():
            logger.warning(f"User {request.user.user_id} is not a member of space {space_id} at {timezone.now()}")
            return Response({"error": "You are not a member of this space"}, status=status.HTTP_403_FORBIDDEN)

        # Rely on SpaceJWTMiddleware for space_jwt
        space_jwt = getattr(request, 'space_jwt', None)
        if not space_jwt or space_jwt.payload['space_id'] != str(space_id):
            logger.error(f"Invalid or missing SpaceJWT for space {space_id} at {timezone.now()}")
            return Response({"error": "Valid SpaceJWT required for this space"}, status=status.HTTP_403_FORBIDDEN)

        # Prepare request data
        data = request.data.copy()
        # Pass user and space directly to serializer
        serializer = self.get_serializer(data=data, context={'user': request.user, 'space': space})
        if serializer.is_valid():
            post = serializer.save(user=request.user, space=space)
            logger.info(f"Post created by user {request.user.user_id} in space {space_id} at {timezone.now()}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        logger.error(f"Post creation failed: {serializer.errors} at {timezone.now()}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UpdatePostView(generics.UpdateAPIView):
    serializer_class = PostUpdateSerializer
    authentication_classes = [SessionAuthentication, JWTAuthentication, SpaceJWTAuthentication]
    permission_classes = [PostPermissions, IsAuthenticated]
    queryset = Post.objects.all()
    lookup_field = 'pk'

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            # Check SpaceJWT
            space_jwt = getattr(request, 'space_jwt', None)
            if not space_jwt:
                logger.error(f"No SpaceJWT provided for user {request.user.user_id} at {timezone.now()}")
                return Response({"error": "A SpaceJWT is required to access this endpoint."}, status=status.HTTP_403_FORBIDDEN)
            if space_jwt.payload['space_id'] != str(instance.space.space_id):
                logger.error(f"SpaceJWT space_id {space_jwt.payload['space_id']} does not match post space {instance.space.space_id} at {timezone.now()}")
                return Response({"error": "SpaceJWT does not match the requested space."}, status=status.HTTP_403_FORBIDDEN)

            # Serialize current state before update
            pre_update_serializer = PostSerializer(instance)
            pre_update_data = pre_update_serializer.data
            logger.info(f"Post {instance.id} retrieved for update by user {request.user.user_id} at {timezone.now()}")

            # Apply update
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                post_update_data = serializer.data
                logger.info(f"Post {instance.id} updated by user {request.user.user_id} at {timezone.now()}")
                return Response({
                    "pre_update": pre_update_data,
                    "post_update": post_update_data
                }, status=status.HTTP_200_OK)
            logger.error(f"Post update failed: {serializer.errors} at {timezone.now()}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Post.DoesNotExist:
            logger.error(f"Post {kwargs.get('pk')} not found at {timezone.now()}")
            return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)

class DeletePostView(generics.DestroyAPIView):
    serializer_class = PostSerializer
    authentication_classes = [SessionAuthentication, JWTAuthentication, SpaceJWTAuthentication]
    permission_classes = [PostPermissions, IsAuthenticated]
    queryset = Post.objects.all()


class ListPostView(generics.ListAPIView):
    serializer_class = PostSerializer
    authentication_classes = [SessionAuthentication, JWTAuthentication, SpaceJWTAuthentication]
    permission_classes = [PostPermissions, IsAuthenticated]

    def get_queryset(self):
        space_id = self.kwargs.get('space_id')
        if space_id:
            try:
                space = Space.objects.get(space_id=space_id)
                return Post.objects.filter(space=space, scheduled_time__gt=timezone.now()).order_by("scheduled_time")
            except Space.DoesNotExist:
                logger.error(f"Space {space_id} not found at {timezone.now()}")
                return Post.objects.none()
        return Post.objects.filter(scheduled_time__gt=timezone.now()).order_by("scheduled_time")

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        # Initialize categorized structure
        categorized_posts = {}
        for platform_choice in Post.PLATFORM_CHOICES:
            platform = platform_choice[0]
            categorized_posts[platform] = {status[0]: [] for status in Post.STATUS_CHOICES}

        # Group posts by platform and status
        for post in queryset:
            for platform in post.platforms:  # Handle multiple platforms per post
                if platform in categorized_posts:
                    status = post.status
                    if status in categorized_posts[platform]:
                        serialized_post = PostSerializer(post).data
                        categorized_posts[platform][status].append(serialized_post)

        post_types = {
            "status_choices": Post.STATUS_CHOICES,
            "platform_choices": Post.PLATFORM_CHOICES
        }
        return Response({
            "post_types": post_types,
            "scheduled_posts": categorized_posts
        })


class RetrievePostView(generics.RetrieveAPIView):
    serializer_class = PostSerializer
    authentication_classes = [SessionAuthentication, JWTAuthentication, SpaceJWTAuthentication]
    permission_classes = [PostPermissions, IsAuthenticated]
    queryset = Post.objects.all()
    lookup_field = 'id'

    def get(self, request, *args, **kwargs):
        try:
            post = self.get_object()
            # Explicitly check SpaceMembership
            if not SpaceMembership.objects.filter(user=request.user, space=post.space).exists():
                logger.warning(f"User {request.user.user_id} is not a member of space {post.space.space_id} for post {post.id} at {timezone.now()}")
                return Response({"error": "You are not a member of the space associated with this post"}, status=status.HTTP_403_FORBIDDEN)

            # Validate SpaceJWT
            space_jwt = getattr(request, 'space_jwt', None)
            if not space_jwt or space_jwt.payload['space_id'] != str(post.space.space_id):
                logger.error(f"Invalid or missing SpaceJWT for space {post.space.space_id} for post {post.id} at {timezone.now()}")
                return Response({"error": "Valid SpaceJWT required for this space"}, status=status.HTTP_403_FORBIDDEN)

            serializer = self.get_serializer(post)
            logger.info(f"Post {post.id} retrieved by user {request.user.user_id} at {timezone.now()}")
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Post.DoesNotExist:
            logger.error(f"Post {kwargs.get('id')} not found at {timezone.now()}")
            return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)