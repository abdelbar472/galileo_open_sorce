import logging
from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions
from rest_framework_simplejwt.tokens import AccessToken
from django.utils import timezone
from outh.models import User

logger = logging.getLogger(__name__)

class SpaceJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        logger.debug(f"Auth header: {auth_header}, Request META: {request.META} at {timezone.now()}")

        if not auth_header:
            logger.warning(f"No Authorization header provided at {timezone.now()}")
            raise exceptions.AuthenticationFailed(
                'No Authorization header provided. Please include a valid header in the format: "Bearer <JWT>" or "SpaceJWT <space_jwt>".'
            )

        if not auth_header.startswith('SpaceJWT '):
            logger.debug(f"Header does not start with 'SpaceJWT'. Passing to other authentication methods at {timezone.now()}")
            return None

        try:
            space_jwt = auth_header.split(' ', 1)[1].strip()
            if not space_jwt:
                logger.error(f"Empty SpaceJWT provided at {timezone.now()}")
                raise exceptions.AuthenticationFailed('Invalid token format. Expected "SpaceJWT <space_jwt>", but token is empty.')
        except IndexError:
            logger.error(f"Malformed Authorization header: {auth_header} at {timezone.now()}")
            raise exceptions.AuthenticationFailed(
                'Invalid Authorization header format. Expected "SpaceJWT <space_jwt>", but header is malformed.'
            )

        try:
            token = AccessToken(space_jwt)
        except Exception as e:
            logger.error(f"Invalid SpaceJWT: {str(e)} at {timezone.now()}")
            raise exceptions.AuthenticationFailed('Invalid SpaceJWT. Please check the token.')

        # Validate token type
        token_type = token.payload.get('token_type')
        if token_type != 'space_jwt':
            logger.error(f"Invalid token type: {token_type}. Expected 'space_jwt' at {timezone.now()}")
            raise exceptions.AuthenticationFailed('Invalid token type. Expected a space JWT.')

        if token.payload['exp'] < timezone.now().timestamp():
            logger.error(f"SpaceJWT has expired at {timezone.now()}")
            raise exceptions.AuthenticationFailed('SpaceJWT has expired. Please obtain a new token.')

        user_id = token.payload.get('user_id')
        try:
            user = User.objects.get(user_id=user_id)
            if not user.is_active:
                logger.error(f"User {user_id} is inactive at {timezone.now()}")
                raise exceptions.AuthenticationFailed('User associated with this SpaceJWT is inactive.')
        except User.DoesNotExist:
            logger.error(f"User {user_id} does not exist at {timezone.now()}")
            raise exceptions.AuthenticationFailed('User associated with this SpaceJWT no longer exists.')

        space_id = token.payload.get('space_id')
        if 'space_pk' in request.parser_context['kwargs'] and space_id != request.parser_context['kwargs']['space_pk']:
            logger.error(f"SpaceJWT space_id {space_id} does not match requested space {request.parser_context['kwargs']['space_pk']} at {timezone.now()}")
            raise exceptions.AuthenticationFailed('SpaceJWT does not match the requested space.')

        # Validate scope
        scope = token.payload.get('scope')
        if not scope:
            logger.error(f"SpaceJWT missing scope claim at {timezone.now()}")
            raise exceptions.AuthenticationFailed('SpaceJWT missing scope claim.')

        logger.debug(f"SpaceJWT authentication successful for user: {user_id}, space: {space_id}, scope: {scope} at {timezone.now()}")
        request.space_jwt = token
        return (user, token)