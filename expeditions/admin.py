from django.contrib import admin

from expeditions.models import Expedition, ExpeditionMember


@admin.register(Expedition)
class ExpeditionAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'status', 'chief', 'capacity', 'start_at', 'created_at')
    list_filter = ('status', 'start_at')
    search_fields = ('title', 'description', 'chief__email')
    autocomplete_fields = ('chief',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ExpeditionMember)
class ExpeditionMemberAdmin(admin.ModelAdmin):
    list_display = ('id', 'expedition', 'user', 'state', 'invited_at', 'confirmed_at')
    list_filter = ('state', 'invited_at')
    search_fields = ('expedition__title', 'user__email')
    autocomplete_fields = ('expedition', 'user')
    readonly_fields = ('invited_at',)
