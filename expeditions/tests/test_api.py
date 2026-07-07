from datetime import timedelta

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def list_url():
    return reverse('expeditions:expedition-list')


def detail_url(pk):
    return reverse('expeditions:expedition-detail', args=[pk])


def action_url(name, pk):
    return reverse(f'expeditions:expedition-{name}', args=[pk])


def invite(chief_client, expedition, member):
    return chief_client.post(
        action_url('invite', expedition.id),
        {'member_id': member.id},
        format='json',
    )


def confirm(member, expedition):
    return auth_client(member).post(action_url('confirm', expedition.id))


def invite_and_confirm(chief_client, expedition, member):
    invite(chief_client, expedition, member)
    confirm(member, expedition)


def test_list_requires_authentication():
    response = APIClient().get(list_url())

    assert response.status_code == 401


def test_chief_can_create_expedition(chief, now):
    response = auth_client(chief).post(
        list_url(),
        {
            'title': 'Summit Ascent',
            'start_at': now.isoformat(),
            'capacity': 5,
        },
        format='json',
    )

    assert response.status_code == 201
    assert response.data['status'] == 'draft'


def test_member_cannot_create_expedition(member, now):
    response = auth_client(member).post(
        list_url(),
        {
            'title': 'Summit Ascent',
            'start_at': now.isoformat(),
            'capacity': 5,
        },
        format='json',
    )

    assert response.status_code == 403


def test_chief_sees_own_expedition(chief, make_expedition):
    expedition = make_expedition(owner=chief)

    response = auth_client(chief).get(list_url())

    assert response.status_code == 200
    assert expedition.id in [row['id'] for row in response.data]


def test_related_member_sees_expedition(chief, make_expedition, confirmed_member):
    expedition = make_expedition(owner=chief)
    user = confirmed_member(expedition)

    response = auth_client(user).get(list_url())

    assert expedition.id in [row['id'] for row in response.data]


def test_unrelated_user_does_not_see_expedition(chief, make_expedition, make_user):
    expedition = make_expedition(owner=chief)

    response = auth_client(make_user()).get(list_url())

    assert expedition.id not in [row['id'] for row in response.data]


def test_retrieve_unrelated_expedition_returns_404(chief, make_expedition, make_user):
    expedition = make_expedition(owner=chief)

    response = auth_client(make_user()).get(detail_url(expedition.id))

    assert response.status_code == 404


def test_chief_can_invite_member(chief, make_expedition, member):
    expedition = make_expedition(owner=chief)

    response = invite(auth_client(chief), expedition, member)

    assert response.status_code == 201
    assert response.data['state'] == 'invited'
    assert response.data['user']['id'] == member.id


def test_invited_member_can_confirm(chief, make_expedition, member):
    expedition = make_expedition(owner=chief)
    invite(auth_client(chief), expedition, member)

    response = confirm(member, expedition)

    assert response.status_code == 200
    assert response.data['state'] == 'confirmed'


def test_duplicate_invite_returns_400(chief, make_expedition, member):
    expedition = make_expedition(owner=chief)
    chief_client = auth_client(chief)
    invite(chief_client, expedition, member)

    response = invite(chief_client, expedition, member)

    assert response.status_code == 400
    assert isinstance(response.data['detail'], str)


def test_non_chief_invite_returns_403(chief, make_expedition, member, confirmed_member):
    expedition = make_expedition(owner=chief)
    insider = confirmed_member(expedition)

    response = invite(auth_client(insider), expedition, member)

    assert response.status_code == 403


def test_full_lifecycle_happy_path(chief, make_expedition, make_user, now):
    expedition = make_expedition(owner=chief, start_at=now - timedelta(hours=1))
    chief_client = auth_client(chief)
    for _ in range(2):
        invite_and_confirm(chief_client, expedition, make_user())

    chief_client.post(action_url('set-ready', expedition.id))
    chief_client.post(action_url('start', expedition.id))
    response = chief_client.post(action_url('finish', expedition.id))

    assert response.status_code == 200
    assert response.data['status'] == 'finished'
    assert response.data['end_at'] is not None


def test_start_too_early_returns_400(chief, make_expedition, make_user, now):
    expedition = make_expedition(owner=chief, start_at=now + timedelta(hours=1))
    chief_client = auth_client(chief)
    for _ in range(2):
        invite_and_confirm(chief_client, expedition, make_user())
    chief_client.post(action_url('set-ready', expedition.id))

    response = chief_client.post(action_url('start', expedition.id))

    assert response.status_code == 400
    assert isinstance(response.data['detail'], str)


def test_non_chief_start_returns_403(chief, make_expedition, make_user, now):
    expedition = make_expedition(owner=chief, start_at=now - timedelta(hours=1))
    chief_client = auth_client(chief)
    members = [make_user(), make_user()]
    for user in members:
        invite_and_confirm(chief_client, expedition, user)
    chief_client.post(action_url('set-ready', expedition.id))

    response = auth_client(members[0]).post(action_url('start', expedition.id))

    assert response.status_code == 403
    assert isinstance(response.data['detail'], str)
