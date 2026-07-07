from django.db.models import Q

from expeditions.models import (
    Expedition,
    ExpeditionMember,
    ExpeditionMemberState,
    ExpeditionStatus,
)


def expeditions_visible_to(*, user):
    """Return expeditions the user leads or participates in, without duplicates."""
    return (
        Expedition.objects.filter(Q(chief=user) | Q(members__user=user))
        .select_related('chief')
        .prefetch_related('members__user')
        .distinct()
    )


def confirmed_member_count(*, expedition):
    return expedition.members.filter(
        state=ExpeditionMemberState.CONFIRMED,
    ).count()


def confirmed_member_user_ids(*, expedition):
    return expedition.members.filter(
        state=ExpeditionMemberState.CONFIRMED,
    ).values_list('user_id', flat=True)


def event_recipient_user_ids(*, expedition):
    """User ids that should receive real-time events for an expedition.

    Recipients are the expedition chief plus every user with an
    ExpeditionMember row, regardless of invitation state.
    """
    member_ids = ExpeditionMember.objects.filter(
        expedition_id=expedition.id,
    ).values_list('user_id', flat=True)
    return {expedition.chief_id, *member_ids}


def user_ids_in_other_active_expedition(*, expedition, user_ids):
    return set(
        ExpeditionMember.objects.filter(
            state=ExpeditionMemberState.CONFIRMED,
            user_id__in=list(user_ids),
            expedition__status=ExpeditionStatus.ACTIVE,
        )
        .exclude(expedition_id=expedition.id)
        .values_list('user_id', flat=True)
    )
