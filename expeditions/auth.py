from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from users.models import User


@database_sync_to_async
def _get_active_user(user_id):
    try:
        return User.objects.get(pk=user_id, is_active=True)
    except User.DoesNotExist:
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """Authenticate WebSocket connections from a JWT access token.

    The access token is read from the ``token`` query-string parameter. A valid
    token attaches the resolved user to ``scope['user']``; a missing, invalid or
    expired token attaches ``AnonymousUser`` so the consumer rejects it.
    """

    async def __call__(self, scope, receive, send):
        query = parse_qs(scope.get('query_string', b'').decode())
        raw_token = query.get('token', [None])[0]
        scope['user'] = await self._resolve_user(raw_token)
        return await super().__call__(scope, receive, send)

    async def _resolve_user(self, raw_token):
        if not raw_token:
            return AnonymousUser()
        try:
            access_token = AccessToken(raw_token)
        except TokenError:
            return AnonymousUser()
        user_id = access_token.get('user_id')
        if user_id is None:
            return AnonymousUser()
        return await _get_active_user(user_id)
