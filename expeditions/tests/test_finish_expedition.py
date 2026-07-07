from datetime import timedelta

import pytest

from expeditions import services
from expeditions.exceptions import InvalidTransitionError, PermissionDeniedError
from expeditions.models import Expedition, ExpeditionStatus


@pytest.mark.django_db
def test_chief_can_move_active_to_finished(ready_expedition, now):
    expedition = ready_expedition()
    services.start_expedition(expedition=expedition, chief=expedition.chief, now=now)

    services.finish_expedition(expedition=expedition, chief=expedition.chief, now=now)

    assert Expedition.objects.get(pk=expedition.pk).status == ExpeditionStatus.FINISHED


@pytest.mark.django_db
def test_end_at_is_set_when_null(ready_expedition, now):
    expedition = ready_expedition()
    assert expedition.end_at is None
    services.start_expedition(expedition=expedition, chief=expedition.chief, now=now)

    services.finish_expedition(expedition=expedition, chief=expedition.chief, now=now)

    assert Expedition.objects.get(pk=expedition.pk).end_at == now


@pytest.mark.django_db
def test_existing_end_at_is_preserved(make_expedition, chief, confirmed_member, now):
    end_at = now + timedelta(days=3)
    expedition = make_expedition(end_at=end_at)
    for _ in range(2):
        confirmed_member(expedition)
    services.set_ready(expedition=expedition, chief=chief)
    services.start_expedition(expedition=expedition, chief=chief, now=now)

    services.finish_expedition(expedition=expedition, chief=chief, now=now)

    assert Expedition.objects.get(pk=expedition.pk).end_at == end_at


@pytest.mark.django_db
def test_non_chief_cannot_finish(ready_expedition, make_user, now):
    expedition = ready_expedition()
    services.start_expedition(expedition=expedition, chief=expedition.chief, now=now)
    intruder = make_user(role='chief')

    with pytest.raises(PermissionDeniedError):
        services.finish_expedition(expedition=expedition, chief=intruder, now=now)

    assert Expedition.objects.get(pk=expedition.pk).status == ExpeditionStatus.ACTIVE


@pytest.mark.django_db
def test_only_active_can_be_finished(ready_expedition, now):
    expedition = ready_expedition()

    with pytest.raises(InvalidTransitionError):
        services.finish_expedition(expedition=expedition, chief=expedition.chief, now=now)

    assert Expedition.objects.get(pk=expedition.pk).status == ExpeditionStatus.READY


@pytest.mark.django_db
def test_finished_expedition_cannot_be_started_again(ready_expedition, now):
    expedition = ready_expedition()
    services.start_expedition(expedition=expedition, chief=expedition.chief, now=now)
    services.finish_expedition(expedition=expedition, chief=expedition.chief, now=now)

    with pytest.raises(InvalidTransitionError):
        services.start_expedition(expedition=expedition, chief=expedition.chief, now=now)

    assert Expedition.objects.get(pk=expedition.pk).status == ExpeditionStatus.FINISHED
