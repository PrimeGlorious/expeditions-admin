from django.db import transaction
from django.utils import timezone

from expeditions import events, selectors
from expeditions.exceptions import (
    ExpeditionStartError,
    InvalidTransitionError,
    InvitationError,
    PermissionDeniedError,
)
from expeditions.models import (
    Expedition,
    ExpeditionMember,
    ExpeditionMemberState,
    ExpeditionStatus,
)
from users.models import UserRole

MIN_CONFIRMED_MEMBERS = 2


def create_expedition(
    *, chief, title, description=None, start_at, end_at=None, capacity
):
    """Create a draft expedition owned by a chief.

    Args:
        chief: User creating the expedition; must have the chief role.
        title: Human-readable expedition title.
        description: Optional free-text description.
        start_at: Planned start datetime.
        end_at: Optional planned end datetime.
        capacity: Maximum number of confirmed members allowed.

    Returns:
        The newly created Expedition in draft status.

    Raises:
        PermissionDeniedError: If the user is not a chief.
    """
    if chief.role != UserRole.CHIEF:
        raise PermissionDeniedError('Only a chief can create an expedition.')

    return Expedition.objects.create(
        chief=chief,
        title=title,
        description=description,
        start_at=start_at,
        end_at=end_at,
        capacity=capacity,
        status=ExpeditionStatus.DRAFT,
    )


@transaction.atomic
def invite_member(*, expedition, chief, member):
    """Invite a member user to a draft expedition.

    Args:
        expedition: Expedition receiving the invitation.
        chief: User performing the invitation; must be the expedition chief.
        member: User being invited; must have the member role.

    Returns:
        The created ExpeditionMember in the invited state.

    Raises:
        PermissionDeniedError: If the actor is not the expedition chief.
        InvitationError: If the target is not a member, the expedition is not
            a draft, or the user was already invited.
    """
    expedition = Expedition.objects.select_for_update().get(pk=expedition.pk)

    if expedition.chief_id != chief.id:
        raise PermissionDeniedError('Only the expedition chief can invite members.')

    if member.role != UserRole.MEMBER:
        raise InvitationError('Only users with the member role can be invited.')

    if expedition.status != ExpeditionStatus.DRAFT:
        raise InvitationError('Members can only be invited while the expedition is a draft.')

    if expedition.members.filter(user_id=member.id).exists():
        raise InvitationError('This user has already been invited to the expedition.')

    expedition_member = ExpeditionMember.objects.create(
        expedition=expedition,
        user=member,
        state=ExpeditionMemberState.INVITED,
    )

    events.dispatch_member_invited(
        expedition=expedition, member_id=expedition_member.user_id
    )

    return expedition_member


@transaction.atomic
def confirm_invitation(*, expedition, member):
    """Confirm the acting user's own invitation.

    Args:
        expedition: Expedition the invitation belongs to.
        member: User confirming their own invitation.

    Returns:
        The updated ExpeditionMember in the confirmed state.

    Raises:
        InvitationError: If the user has no invitation to this expedition.
        InvalidTransitionError: If the invitation is not in the invited state.
    """
    try:
        expedition_member = (
            ExpeditionMember.objects.select_for_update()
            .get(expedition_id=expedition.id, user_id=member.id)
        )
    except ExpeditionMember.DoesNotExist:
        raise InvitationError('You have no invitation to this expedition.') from None

    if expedition_member.state != ExpeditionMemberState.INVITED:
        raise InvalidTransitionError('Only an invited membership can be confirmed.')

    expedition_member.state = ExpeditionMemberState.CONFIRMED
    expedition_member.confirmed_at = timezone.now()
    expedition_member.save(update_fields=('state', 'confirmed_at'))

    events.dispatch_member_confirmed(
        expedition=expedition, member_id=expedition_member.user_id
    )

    return expedition_member


@transaction.atomic
def set_ready(*, expedition, chief):
    """Move a draft expedition to the ready status.

    Raises:
        PermissionDeniedError: If the actor is not the expedition chief.
        InvalidTransitionError: If the expedition is not a draft.
    """
    expedition = Expedition.objects.select_for_update().get(pk=expedition.pk)

    if expedition.chief_id != chief.id:
        raise PermissionDeniedError('Only the expedition chief can set the expedition ready.')

    if expedition.status != ExpeditionStatus.DRAFT:
        raise InvalidTransitionError('Only a draft expedition can be set ready.')

    expedition.status = ExpeditionStatus.READY
    expedition.save(update_fields=('status',))

    events.dispatch_expedition_status(expedition=expedition)

    return expedition


@transaction.atomic
def start_expedition(*, expedition, chief, now=None):
    """Start a ready expedition, enforcing all start preconditions.

    Args:
        expedition: Expedition to start.
        chief: User starting the expedition; must be the expedition chief.
        now: Reference time for the start check; defaults to the current time.

    Returns:
        The updated Expedition in the active status.

    Raises:
        PermissionDeniedError: If the actor is not the expedition chief.
        InvalidTransitionError: If the expedition is not ready.
        ExpeditionStartError: If start_at is in the future, the confirmed
            member count is out of range, or a confirmed member is already in
            another active expedition.
    """
    now = now or timezone.now()
    expedition = Expedition.objects.select_for_update().get(pk=expedition.pk)

    if expedition.chief_id != chief.id:
        raise PermissionDeniedError('Only the expedition chief can start the expedition.')

    if expedition.status != ExpeditionStatus.READY:
        raise InvalidTransitionError('Only a ready expedition can be started.')

    if expedition.start_at > now:
        raise ExpeditionStartError('The expedition cannot start before its start time.')

    confirmed_count = selectors.confirmed_member_count(expedition=expedition)
    if confirmed_count < MIN_CONFIRMED_MEMBERS:
        raise ExpeditionStartError(
            f'At least {MIN_CONFIRMED_MEMBERS} confirmed members are required to start.'
        )
    if confirmed_count > expedition.capacity:
        raise ExpeditionStartError('Confirmed members exceed the expedition capacity.')

    user_ids = selectors.confirmed_member_user_ids(expedition=expedition)
    busy_user_ids = selectors.user_ids_in_other_active_expedition(
        expedition=expedition, user_ids=user_ids
    )
    if busy_user_ids:
        raise ExpeditionStartError('A confirmed member is already in another active expedition.')

    expedition.status = ExpeditionStatus.ACTIVE
    expedition.save(update_fields=('status',))

    events.dispatch_expedition_status(expedition=expedition)

    return expedition


@transaction.atomic
def finish_expedition(*, expedition, chief, now=None):
    """Finish an active expedition.

    Args:
        expedition: Expedition to finish.
        chief: User finishing the expedition; must be the expedition chief.
        now: End timestamp used when end_at is not already set.

    Returns:
        The updated Expedition in the finished status.

    Raises:
        PermissionDeniedError: If the actor is not the expedition chief.
        InvalidTransitionError: If the expedition is not active.
    """
    now = now or timezone.now()
    expedition = Expedition.objects.select_for_update().get(pk=expedition.pk)

    if expedition.chief_id != chief.id:
        raise PermissionDeniedError('Only the expedition chief can finish the expedition.')

    if expedition.status != ExpeditionStatus.ACTIVE:
        raise InvalidTransitionError('Only an active expedition can be finished.')

    expedition.status = ExpeditionStatus.FINISHED
    update_fields = ['status']
    if expedition.end_at is None:
        expedition.end_at = now
        update_fields.append('end_at')

    expedition.save(update_fields=update_fields)

    events.dispatch_expedition_status(expedition=expedition)

    return expedition
