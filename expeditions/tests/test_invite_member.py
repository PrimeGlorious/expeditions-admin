import pytest

from expeditions import services
from expeditions.exceptions import InvitationError, PermissionDeniedError
from expeditions.models import ExpeditionMember, ExpeditionMemberState, ExpeditionStatus


@pytest.mark.django_db
def test_chief_can_invite_member(make_expedition, member):
    expedition = make_expedition()

    invitation = services.invite_member(
        expedition=expedition, chief=expedition.chief, member=member
    )

    assert invitation.state == ExpeditionMemberState.INVITED
    assert invitation.confirmed_at is None
    stored = ExpeditionMember.objects.get(pk=invitation.pk)
    assert stored.user_id == member.id
    assert stored.expedition_id == expedition.id


@pytest.mark.django_db
def test_non_chief_cannot_invite(make_expedition, make_user, member):
    expedition = make_expedition()
    other_chief = make_user(role='chief')

    with pytest.raises(PermissionDeniedError):
        services.invite_member(
            expedition=expedition, chief=other_chief, member=member
        )

    assert ExpeditionMember.objects.count() == 0


@pytest.mark.django_db
def test_chief_role_cannot_be_invited_as_member(make_expedition, make_user):
    expedition = make_expedition()
    another_chief = make_user(role='chief')

    with pytest.raises(InvitationError):
        services.invite_member(
            expedition=expedition, chief=expedition.chief, member=another_chief
        )

    assert ExpeditionMember.objects.count() == 0


@pytest.mark.django_db
def test_duplicate_invitation_is_rejected(make_expedition, member):
    expedition = make_expedition()
    services.invite_member(
        expedition=expedition, chief=expedition.chief, member=member
    )

    with pytest.raises(InvitationError):
        services.invite_member(
            expedition=expedition, chief=expedition.chief, member=member
        )

    assert ExpeditionMember.objects.filter(
        expedition=expedition, user=member
    ).count() == 1


@pytest.mark.django_db
def test_invitation_only_allowed_while_draft(ready_expedition, member):
    expedition = ready_expedition()
    assert expedition.status == ExpeditionStatus.READY

    with pytest.raises(InvitationError):
        services.invite_member(
            expedition=expedition, chief=expedition.chief, member=member
        )

    assert not ExpeditionMember.objects.filter(user=member).exists()
