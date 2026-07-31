from django.contrib import admin

from .models import (AccessProfile, TaskSession, AccessCard, ConsentGrant,
                     AuditEvent, Phrase)


@admin.register(AccessProfile)
class AccessProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "is_default", "updated_at")
    list_filter = ("is_default",)


@admin.register(TaskSession)
class TaskSessionAdmin(admin.ModelAdmin):
    list_display = ("goal", "owner", "status", "source_type", "updated_at")
    list_filter = ("status", "source_type")


@admin.register(AccessCard)
class AccessCardAdmin(admin.ModelAdmin):
    list_display = ("session", "sequence", "card_type", "requires_confirmation")
    list_filter = ("card_type",)


@admin.register(ConsentGrant)
class ConsentGrantAdmin(admin.ModelAdmin):
    list_display = ("grantee_label", "owner", "is_active", "expires_at")


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("action", "owner", "detail", "created_at")


@admin.register(Phrase)
class PhraseAdmin(admin.ModelAdmin):
    list_display = ("text", "owner", "pack", "order")
