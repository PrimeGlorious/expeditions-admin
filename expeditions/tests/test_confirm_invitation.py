import pytest

from expeditions import services
from expeditions.exceptions import InvalidTransitionError, InvitationError
from expeditions.models import ExpeditionMember, ExpeditionMemberState


@pytest.mark.django_db
def test_invited_member_can_confirm_own_invitation(make_expedition, member):
    expedition = make_expedition()
    services.invite_member(
        expedition=expedition, chief=expedition.chief, member=member
    )

    confirmed = services.confirm_invitation(expedition=expedition, member=member)

    assert confirmed.state == ExpeditionMemberState.CONFIRMED


@pytest.mark.django_db
def test_confirmed_at_is_set(make_expedition, member):
    expedition = make_expedition()
    services.invite_member(
        expedition=expedition, chief=expedition.chief, member=member
    )

    services.confirm_invitation(expedition=expedition, member=member)

    stored = ExpeditionMember.objects.get(expedition=expedition, user=member)
    assert stored.confirmed_at is not None


@pytest.mark.django_db
def test_uninvited_user_cannot_confirm(make_expedition, member):
    expedition = make_expedition()

    with pytest.raises(InvitationError):
        services.confirm_invitation(expedition=expedition, member=member)


@pytest.mark.django_db
def test_already_confirmed_invitation_cannot_be_confirmed_again(
    make_expedition, member
):
    expedition = make_expedition()
    services.invite_member(
        expedition=expedition, chief=expedition.chief, member=member
    )
    first = services.confirm_invitation(expedition=expedition, member=member)

    with pytest.raises(InvalidTransitionError):
        services.confirm_invitation(expedition=expedition, member=member)

    stored = ExpeditionMember.objects.get(expedition=expedition, user=member)
    assert stored.confirmed_at == first.confirmed_at
