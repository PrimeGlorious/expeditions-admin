from datetime import timedelta

import pytest
from django.utils import timezone

from expeditions import services
from expeditions.models import ExpeditionMemberState
from users.models import User, UserRole


@pytest.fixture
def now():
    return timezone.now()


@pytest.fixture
def make_user(db):
    counter = {'value': 0}

    def _make_user(role=UserRole.MEMBER, **kwargs):
        counter['value'] += 1
        email = kwargs.pop('email', f'user{counter["value"]}@example.com')
        return User.objects.create_user(
            email=email,
            password='pass1234',
            role=role,
            **kwargs,
        )

    return _make_user


@pytest.fixture
def chief(make_user):
    return make_user(role=UserRole.CHIEF)


@pytest.fixture
def member(make_user):
    return make_user(role=UserRole.MEMBER)


@pytest.fixture
def make_expedition(chief, now):
    def _make_expedition(*, owner=None, start_at=None, capacity=5, **kwargs):
        return services.create_expedition(
            chief=owner or chief,
            title=kwargs.pop('title', 'Summit Ascent'),
            start_at=start_at or (now - timedelta(hours=1)),
            capacity=capacity,
            **kwargs,
        )

    return _make_expedition


@pytest.fixture
def confirmed_member(make_user):
    def _confirmed_member(expedition):
        user = make_user(role=UserRole.MEMBER)
        services.invite_member(
            expedition=expedition, chief=expedition.chief, member=user
        )
        services.confirm_invitation(expedition=expedition, member=user)
        return user

    return _confirmed_member


@pytest.fixture
def ready_expedition(make_expedition, chief, confirmed_member):
    def _ready_expedition(*, confirmed=2, capacity=5, start_at=None):
        expedition = make_expedition(capacity=capacity, start_at=start_at)
        for _ in range(confirmed):
            confirmed_member(expedition)
        services.set_ready(expedition=expedition, chief=chief)
        expedition.refresh_from_db()
        return expedition

    return _ready_expedition


@pytest.fixture
def invited_states():
    return ExpeditionMemberState
