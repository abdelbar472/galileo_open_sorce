# root_app/root_app/asgi.py
import os
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.layers import get_channel_layer

# Set DJANGO_SETTINGS_MODULE and initialize Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'galileo.settings')
django.setup()

# Import middleware and routing after Django setup
from chat.middleware import JWTAuthMiddleware
from chat.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": JWTAuthMiddleware(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})

channel_layer = get_channel_layer()