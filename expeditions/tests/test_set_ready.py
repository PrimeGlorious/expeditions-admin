import pytest

from expeditions import services
from expeditions.exceptions import InvalidTransitionError, PermissionDeniedError
from expeditions.models import Expedition, ExpeditionStatus


@pytest.mark.django_db
def test_chief_can_move_draft_to_ready(make_expedition):
    expedition = make_expedition()

    services.set_ready(expedition=expedition, chief=expedition.chief)

    assert Expedition.objects.get(pk=expedition.pk).status == ExpeditionStatus.READY


@pytest.mark.django_db
def test_non_chief_cannot_set_ready(make_expedition, make_user):
    expedition = make_expedition()
    other_chief = make_user(role='chief')

    with pytest.raises(PermissionDeniedError):
        services.set_ready(expedition=expedition, chief=other_chief)

    assert Expedition.objects.get(pk=expedition.pk).status == ExpeditionStatus.DRAFT


@pytest.mark.django_db
def test_ready_can_only_come_from_draft(make_expedition):
    expedition = make_expedition()
    services.set_ready(expedition=expedition, chief=expedition.chief)

    with pytest.raises(InvalidTransitionError):
        services.set_ready(expedition=expedition, chief=expedition.chief)


@pytest.mark.django_db
def test_finished_cannot_go_back_to_ready(ready_expedition):
    expedition = ready_expedition()
    services.start_expedition(expedition=expedition, chief=expedition.chief)
    services.finish_expedition(expedition=expedition, chief=expedition.chief)

    with pytest.raises(InvalidTransitionError):
        services.set_ready(expedition=expedition, chief=expedition.chief)

    assert Expedition.objects.get(pk=expedition.pk).status == ExpeditionStatus.FINISHED


@pytest.mark.django_db
def test_active_cannot_go_back_to_ready(ready_expedition):
    expedition = ready_expedition()
    services.start_expedition(expedition=expedition, chief=expedition.chief)

    with pytest.raises(InvalidTransitionError):
        services.set_ready(expedition=expedition, chief=expedition.chief)

    assert Expedition.objects.get(pk=expedition.pk).status == ExpeditionStatus.ACTIVE
