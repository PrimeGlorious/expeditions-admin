from datetime import timedelta

import pytest
from django.db import IntegrityError, transaction

from expeditions.models import Expedition, ExpeditionMember, ExpeditionMemberState


@pytest.mark.django_db
def test_capacity_must_be_at_least_one(chief, now):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Expedition.objects.create(
                chief=chief,
                title='Zero Capacity',
                start_at=now + timedelta(days=1),
                capacity=0,
            )


@pytest.mark.django_db
def test_same_user_cannot_be_linked_twice_to_expedition(
    make_expedition, member
):
    expedition = make_expedition()
    ExpeditionMember.objects.create(
        expedition=expedition,
        user=member,
        state=ExpeditionMemberState.INVITED,
    )

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            ExpeditionMember.objects.create(
                expedition=expedition,
                user=member,
                state=ExpeditionMemberState.INVITED,
            )
