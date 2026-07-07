from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from expeditions.exceptions import (
    ExpeditionStartError,
    InvalidTransitionError,
    InvitationError,
    PermissionDeniedError,
)

DOMAIN_EXCEPTION_STATUS = {
    PermissionDeniedError: status.HTTP_403_FORBIDDEN,
    InvalidTransitionError: status.HTTP_400_BAD_REQUEST,
    InvitationError: status.HTTP_400_BAD_REQUEST,
    ExpeditionStartError: status.HTTP_400_BAD_REQUEST,
}


def domain_exception_handler(exc, context):
    """Translate expedition domain exceptions into clean DRF responses.

    Falls back to the default DRF handler for any non-domain exception so that
    validation, authentication and framework errors keep their usual behaviour.
    """
    for exc_type, status_code in DOMAIN_EXCEPTION_STATUS.items():
        if isinstance(exc, exc_type):
            return Response({'detail': str(exc)}, status=status_code)
    return drf_exception_handler(exc, context)
