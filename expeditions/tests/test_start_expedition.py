from datetime import timedelta

import pytest

from expeditions import services
from expeditions.exceptions import (
    ExpeditionStartError,
    InvalidTransitionError,
    PermissionDeniedError,
)
from expeditions.models import Expedition, ExpeditionStatus


def build_ready_expedition(chief, members, *, capacity, start_at):
    expedition = services.create_expedition(
        chief=chief,
        title='Glacier Crossing',
        start_at=start_at,
        capacity=capacity,
    )
    for user in members:
        services.invite_member(expedition=expedition, chief=chief, member=user)
        services.confirm_invitation(expedition=expedition, member=user)
    services.set_ready(expedition=expedition, chief=chief)
    expedition.refresh_from_db()
    return expedition


@pytest.mark.django_db
def test_chief_starts_ready_expedition_when_all_conditions_met(
    chief, make_user, now
):
    members = [make_user() for _ in range(2)]
    expedition = build_ready_expedition(
        chief, members, capacity=5, start_at=now - timedelta(hours=1)
    )

    services.start_expedition(expedition=expedition, chief=chief, now=now)

    assert Expedition.objects.get(pk=expedition.pk).status == ExpeditionStatus.ACTIVE


@pytest.mark.django_db
def test_cannot_start_before_start_at(chief, make_user, now):
    members = [make_user() for _ in range(2)]
    expedition = build_ready_expedition(
        chief, members, capacity=5, start_at=now + timedelta(hours=1)
    )

    with pytest.raises(ExpeditionStartError):
        services.start_expedition(expedition=expedition, chief=chief, now=now)

    assert Expedition.objects.get(pk=expedition.pk).status == ExpeditionStatus.READY


@pytest.mark.django_db
def test_cannot_start_with_fewer_than_two_confirmed(chief, make_user, now):
    members = [make_user()]
    expedition = build_ready_expedition(
        chief, members, capacity=5, start_at=now - timedelta(hours=1)
    )

    with pytest.raises(ExpeditionStartError):
        services.start_expedition(expedition=expedition, chief=chief, now=now)

    assert Expedition.objects.get(pk=expedition.pk).status == ExpeditionStatus.READY


@pytest.mark.django_db
def test_cannot_start_when_confirmed_exceeds_capacity(chief, make_user, now):
    members = [make_user() for _ in range(3)]
    expedition = build_ready_expedition(
        chief, members, capacity=2, start_at=now - timedelta(hours=1)
    )

    with pytest.raises(ExpeditionStartError):
        services.start_expedition(expedition=expedition, chief=chief, now=now)

    assert Expedition.objects.get(pk=expedition.pk).status == ExpeditionStatus.READY


@pytest.mark.django_db
def test_cannot_start_if_member_in_another_active_expedition(
    chief, make_user, now
):
    shared = make_user()
    first = build_ready_expedition(
        chief, [shared, make_user()], capacity=5, start_at=now - timedelta(hours=1)
    )
    services.start_expedition(expedition=first, chief=chief, now=now)

    second = build_ready_expedition(
        chief, [shared, make_user()], capacity=5, start_at=now - timedelta(hours=1)
    )

    with pytest.raises(ExpeditionStartError):
        services.start_expedition(expedition=second, chief=chief, now=now)

    assert Expedition.objects.get(pk=second.pk).status == ExpeditionStatus.READY


@pytest.mark.django_db
def test_non_chief_cannot_start(chief, make_user, now):
    members = [make_user() for _ in range(2)]
    expedition = build_ready_expedition(
        chief, members, capacity=5, start_at=now - timedelta(hours=1)
    )
    intruder = make_user(role='chief')

    with pytest.raises(PermissionDeniedError):
        services.start_expedition(expedition=expedition, chief=intruder, now=now)

    assert Expedition.objects.get(pk=expedition.pk).status == ExpeditionStatus.READY


@pytest.mark.django_db
def test_draft_cannot_start_directly(chief, make_user, now):
    expedition = services.create_expedition(
        chief=chief,
        title='Glacier Crossing',
        start_at=now - timedelta(hours=1),
        capacity=5,
    )
    for user in (make_user(), make_user()):
        services.invite_member(expedition=expedition, chief=chief, member=user)
        services.confirm_invitation(expedition=expedition, member=user)

    with pytest.raises(InvalidTransitionError):
        services.start_expedition(expedition=expedition, chief=chief, now=now)

    assert Expedition.objects.get(pk=expedition.pk).status == ExpeditionStatus.DRAFT
