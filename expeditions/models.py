from django.conf import settings
from django.db import models


class ExpeditionStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    READY = 'ready', 'Ready'
    ACTIVE = 'active', 'Active'
    FINISHED = 'finished', 'Finished'


class ExpeditionMemberState(models.TextChoices):
    INVITED = 'invited', 'Invited'
    CONFIRMED = 'confirmed', 'Confirmed'


class Expedition(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=16,
        choices=ExpeditionStatus.choices,
        default=ExpeditionStatus.DRAFT,
    )
    start_at = models.DateTimeField()
    end_at = models.DateTimeField(blank=True, null=True)
    capacity = models.PositiveIntegerField()
    chief = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='led_expeditions',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)
        constraints = [
            models.CheckConstraint(
                condition=models.Q(capacity__gte=1),
                name='expedition_capacity_gte_1',
            ),
        ]

    def __str__(self):
        return self.title


class ExpeditionMember(models.Model):
    expedition = models.ForeignKey(
        Expedition,
        on_delete=models.CASCADE,
        related_name='members',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='expedition_memberships',
    )
    state = models.CharField(
        max_length=16,
        choices=ExpeditionMemberState.choices,
        default=ExpeditionMemberState.INVITED,
    )
    invited_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ('-invited_at',)
        constraints = [
            models.UniqueConstraint(
                fields=('expedition', 'user'),
                name='unique_expedition_member',
            ),
        ]

    def __str__(self):
        return f'{self.user} @ {self.expedition}'
