"""
ASGI config for sungrip_backend project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os
import logging
from urllib.parse import urlparse

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sungrip_backend.settings')

# get_asgi_application() calls django.setup(), which must happen BEFORE
# importing any module that touches Django models (e.g. consumers, routing).
from django.core.asgi import get_asgi_application
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from django.conf import settings

from conversations.routing import websocket_urlpatterns
from sungrip_backend.jwt_middleware import JWTAuthMiddleware

logger = logging.getLogger(__name__)


class CorsOriginValidator:
    """
    Channels middleware that validates the WebSocket Origin header against
    Django's CORS_ALLOWED_ORIGINS and ALLOWED_HOSTS.

    AllowedHostsOriginValidator only checks ALLOWED_HOSTS, which may not
    include the frontend domain (e.g. zimgrow.shop) when the API lives on a
    separate subdomain (api.zimgrow.shop).
    """

    def __init__(self, application):
        self.application = application

    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket":
            headers = dict(scope.get("headers", []))
            origin = headers.get(b"origin", b"").decode()

            if origin and not self._origin_allowed(origin):
                logger.warning("WS rejected: origin %s not in CORS_ALLOWED_ORIGINS or ALLOWED_HOSTS", origin)
                # Reject by closing before accept (Daphne sends 403)
                await send({"type": "websocket.close", "code": 4003})
                return

        return await self.application(scope, receive, send)

    @staticmethod
    def _origin_allowed(origin):
        parsed = urlparse(origin)
        origin_host = parsed.hostname or ""

        # Check CORS_ALLOWED_ORIGINS (full URLs like "https://zimgrow.shop")
        cors_origins = getattr(settings, "CORS_ALLOWED_ORIGINS", [])
        if origin in cors_origins:
            return True

        # Fallback: check if origin hostname is in ALLOWED_HOSTS
        allowed_hosts = getattr(settings, "ALLOWED_HOSTS", [])
        if origin_host in allowed_hosts or "*" in allowed_hosts:
            return True

        return False


application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": CorsOriginValidator(
        JWTAuthMiddleware(
            URLRouter(websocket_urlpatterns)
        )
    ),
})
