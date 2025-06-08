# space_jwt_middleware.py
from datetime import timedelta

from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken
from django.conf import settings
from space.models import SpaceMembership, Space
import logging

logger = logging.getLogger(__name__)

class SpaceJWTMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only apply to authenticated requests
        if hasattr(request, 'user') and request.user.is_authenticated:
            try:
                membership = SpaceMembership.objects.filter(user=request.user).first()
                if membership:
                    space = membership.space
                    space_token = AccessToken()
                    space_token['user_id'] = str(request.user.user_id)
                    space_token['space_id'] = str(space.space_id)
                    space_token['role'] = membership.role
                    space_token['is_admin'] = membership.is_admin
                    space_token['scope'] = 'write'  # Default scope
                    space_token['token_type'] = 'space_jwt'
                    space_token['iat'] = timezone.now().timestamp()
                    space_token.set_exp(lifetime=timedelta(days=1))  # 1-day expiration
                    request.space_jwt = space_token
                    logger.info(f"Automatically generated SpaceJWT for user {request.user.user_id} in space {space.space_id} at {timezone.now()}")
                else:
                    logger.warning(f"No space membership found for user {request.user.user_id} at {timezone.now()}")
            except Exception as e:
                logger.error(f"Error generating SpaceJWT in middleware: {str(e)} at {timezone.now()}")

        response = self.get_response(request)
        return response