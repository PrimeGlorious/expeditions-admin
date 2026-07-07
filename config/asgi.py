"""ASGI config for the config project.

Routes HTTP traffic through the standard Django application and serves
WebSocket traffic through Channels. WebSocket connections are authenticated
from a JWT access token before reaching the expedition consumers.
"""

import os

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

django_asgi_application = get_asgi_application()

from expeditions.auth import JWTAuthMiddleware  # noqa: E402
from expeditions.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        'http': django_asgi_application,
        'websocket': AllowedHostsOriginValidator(
            JWTAuthMiddleware(URLRouter(websocket_urlpatterns))
        ),
    }
)
