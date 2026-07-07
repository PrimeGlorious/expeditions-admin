class ExpeditionDomainError(Exception):
    pass


class PermissionDeniedError(ExpeditionDomainError):
    pass


class InvalidTransitionError(ExpeditionDomainError):
    pass


class InvitationError(ExpeditionDomainError):
    pass


class ExpeditionStartError(ExpeditionDomainError):
    pass
