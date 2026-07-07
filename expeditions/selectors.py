from expeditions.models import (
    ExpeditionMember,
    ExpeditionMemberState,
    ExpeditionStatus,
)


def confirmed_member_count(*, expedition):
    return expedition.members.filter(
        state=ExpeditionMemberState.CONFIRMED,
    ).count()


def confirmed_member_user_ids(*, expedition):
    return expedition.members.filter(
        state=ExpeditionMemberState.CONFIRMED,
    ).values_list('user_id', flat=True)


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
