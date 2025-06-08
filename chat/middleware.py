# chat/middleware.py
import jwt
from outh.models import User  # Keep your custom User import
from django.contrib.auth.models import AnonymousUser
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.conf import settings
from urllib.parse import parse_qs
import logging
from rest_framework_simplejwt.tokens import AccessToken

logger = logging.getLogger(__name__)


@database_sync_to_async
def get_user_by_token(token):
    try:
        # Validate token using SimpleJWT
        access_token = AccessToken(token)
        user_id = access_token['user_id']
        if not user_id:
            return AnonymousUser()
        user = User.objects.get(user_id=user_id)
        return user
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, User.DoesNotExist) as e:
        logger.error(f"Token authentication failed: {str(e)}")
        return AnonymousUser()

class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        if scope['type'] != 'websocket':
            return await super().__call__(scope, receive, send)

        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        token = None

        if 'token' in query_params:
            token = query_params['token'][0]

        if not token:
            headers = dict(scope.get('headers', []))
            auth_header = headers.get(b'authorization', b'').decode()
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]

        scope['user'] = await get_user_by_token(token) if token else AnonymousUser()
        return await super().__call__(scope, receive, send)