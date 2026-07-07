import pytest

from expeditions import events, selectors, services
from expeditions.exceptions import InvitationError
from users.models import UserRole


@pytest.mark.django_db
def test_event_recipients_include_chief_and_all_members(
    chief, make_expedition, make_user
):
    expedition = make_expedition()
    invited = make_user(role=UserRole.MEMBER)
    services.invite_member(expedition=expedition, chief=chief, member=invited)
    confirmed = make_user(role=UserRole.MEMBER)
    services.invite_member(expedition=expedition, chief=chief, member=confirmed)
    services.confirm_invitation(expedition=expedition, member=confirmed)
    outsider = make_user(role=UserRole.MEMBER)

    recipients = selectors.event_recipient_user_ids(expedition=expedition)

    assert recipients == {chief.id, invited.id, confirmed.id}
    assert outsider.id not in recipients


class _RecordingChannelLayer:
    def __init__(self):
        self.sent = []

    async def group_send(self, group, message):
        self.sent.append((group, message))


@pytest.mark.django_db
def test_invite_member_dispatches_after_commit(
    monkeypatch, django_capture_on_commit_callbacks, chief, member, make_expedition
):
    layer = _RecordingChannelLayer()
    monkeypatch.setattr(events, 'get_channel_layer', lambda: layer)
    expedition = make_expedition()

    with django_capture_on_commit_callbacks(execute=True):
        services.invite_member(
            expedition=expedition, chief=chief, member=member
        )

    groups = {group for group, _ in layer.sent}
    assert events.user_group_name(chief.id) in groups
    assert events.user_group_name(member.id) in groups

    payloads = [message['payload'] for _, message in layer.sent]
    assert all(payload['type'] == 'member_invited' for payload in payloads)
    assert all(payload['expedition_id'] == expedition.id for payload in payloads)
    assert all(payload['member_id'] == member.id for payload in payloads)


@pytest.mark.django_db
def test_events_not_dispatched_when_transaction_rolls_back(
    monkeypatch, django_capture_on_commit_callbacks, chief, member, make_expedition
):
    layer = _RecordingChannelLayer()
    monkeypatch.setattr(events, 'get_channel_layer', lambda: layer)
    expedition = make_expedition()
    services.invite_member(expedition=expedition, chief=chief, member=member)

    with django_capture_on_commit_callbacks(execute=True):
        with pytest.raises(InvitationError):
            services.invite_member(
                expedition=expedition, chief=chief, member=member
            )

    assert layer.sent == []
