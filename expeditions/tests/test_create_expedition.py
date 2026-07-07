from datetime import timedelta

import pytest

from expeditions import services
from expeditions.exceptions import PermissionDeniedError
from expeditions.models import Expedition, ExpeditionStatus


@pytest.mark.django_db
def test_chief_can_create_expedition(chief, now):
    expedition = services.create_expedition(
        chief=chief,
        title='Ridge Traverse',
        start_at=now + timedelta(days=1),
        capacity=4,
    )

    stored = Expedition.objects.get(pk=expedition.pk)
    assert stored.chief_id == chief.id
    assert stored.title == 'Ridge Traverse'
    assert stored.capacity == 4


@pytest.mark.django_db
def test_created_expedition_starts_as_draft(chief, now):
    expedition = services.create_expedition(
        chief=chief,
        title='Ridge Traverse',
        start_at=now + timedelta(days=1),
        capacity=4,
    )

    assert expedition.status == ExpeditionStatus.DRAFT
    assert Expedition.objects.get(pk=expedition.pk).status == ExpeditionStatus.DRAFT


@pytest.mark.django_db
def test_member_cannot_create_expedition(member, now):
    with pytest.raises(PermissionDeniedError):
        services.create_expedition(
            chief=member,
            title='Ridge Traverse',
            start_at=now + timedelta(days=1),
            capacity=4,
        )

    assert Expedition.objects.count() == 0
