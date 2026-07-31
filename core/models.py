"""
AccessWeave data models.

Design notes
------------
* The Access Passport stores *functional preferences*, never a diagnosis.
* Task input (the original label / form / text) is kept only while the task is
  active and is erased on completion or deletion when the profile asks for it.
* Audit events record *that* a consequential action happened, with minimal
  metadata — never the private content itself.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class AccessProfile(models.Model):
    """A portable 'Access Passport' — how the user wants software to behave."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="access_profiles",
    )
    name = models.CharField(max_length=100)
    schema_version = models.CharField(max_length=20, default="0.1")
    payload = models.JSONField(default=dict)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_default", "name"]

    def __str__(self):
        return f"{self.name} ({self.owner})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_default:
            # Exactly one default per owner.
            AccessProfile.objects.filter(owner=self.owner).exclude(
                pk=self.pk
            ).update(is_default=False)


class TaskSession(models.Model):
    """The central unit of work: turning one inaccessible thing into a path."""

    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not started"
        ANALYZING = "analyzing", "Analyzing"
        READY = "ready", "Ready"
        IN_PROGRESS = "in_progress", "In progress"
        WAITING_FOR_USER = "waiting_for_user", "Waiting for you"
        BLOCKED = "blocked", "Blocked"
        NEEDS_SUPPORT = "needs_support", "Needs support"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="task_sessions",
    )
    goal = models.CharField(max_length=300)
    source_type = models.CharField(max_length=30, default="text")
    status = models.CharField(
        max_length=30, choices=Status.choices, default=Status.NOT_STARTED
    )
    active_profile = models.ForeignKey(
        AccessProfile, null=True, blank=True, on_delete=models.SET_NULL
    )
    # The raw source content the user provided (pasted text / OCR output).
    # Erased when the retention policy says so.
    source_text = models.TextField(blank=True, default="")
    # Structured analysis + task graph produced by the compiler.
    analysis = models.JSONField(default=dict, blank=True)
    task_graph = models.JSONField(default=dict, blank=True)
    current_step = models.PositiveIntegerField(default=0)
    retention_policy = models.CharField(
        max_length=30, default="delete_on_completion"
    )
    no_storage = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.goal[:40]} [{self.status}]"

    @property
    def card_count(self):
        return self.cards.count()

    def purge_source(self):
        """Erase the original private input while keeping the accessible path."""
        self.source_text = ""
        self.save(update_fields=["source_text", "updated_at"])


class AccessCard(models.Model):
    """A small, predictable interface object rendered in the user's format."""

    class CardType(models.TextChoices):
        SUMMARY = "summary", "Summary"
        INSTRUCTION = "instruction", "Instruction"
        INFORMATION = "information", "Information"
        CHECKLIST = "checklist", "Checklist"
        CHOICE = "choice", "Choice"
        WARNING = "warning", "Warning"
        COMMUNICATION = "communication", "Communication"
        CONFIRMATION = "confirmation", "Confirmation"
        RECOVERY = "recovery", "Recovery"
        COMPLETION = "completion", "Completion"

    session = models.ForeignKey(
        TaskSession, on_delete=models.CASCADE, related_name="cards"
    )
    sequence = models.PositiveIntegerField()
    card_type = models.CharField(max_length=30, choices=CardType.choices)
    payload = models.JSONField(default=dict)
    confidence = models.FloatField(null=True, blank=True)
    requires_confirmation = models.BooleanField(default=False)
    status = models.CharField(max_length=30, default="pending")

    class Meta:
        ordering = ["session_id", "sequence"]
        unique_together = ("session", "sequence")

    def __str__(self):
        return f"[{self.sequence}] {self.card_type}"


class ConsentGrant(models.Model):
    """A scoped, expiring permission for a supporter — never a full account key."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="granted_consents",
    )
    grantee_label = models.CharField(max_length=120)
    scope = models.JSONField(default=dict)
    reason = models.CharField(max_length=200, blank=True, default="")
    starts_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_active(self):
        now = timezone.now()
        if self.revoked_at is not None:
            return False
        return self.starts_at <= now < self.expires_at

    def __str__(self):
        return f"{self.grantee_label} ({'active' if self.is_active else 'inactive'})"


class AuditEvent(models.Model):
    """Minimal record that a consequential action happened. No private content."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="audit_events",
    )
    action = models.CharField(max_length=60)
    detail = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} @ {self.created_at:%Y-%m-%d %H:%M}"


class Phrase(models.Model):
    """A saved quick message for the Communication Bridge."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="phrases",
    )
    pack = models.CharField(max_length=40, default="general")
    text = models.CharField(max_length=200)
    symbol = models.CharField(max_length=8, blank=True, default="")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["pack", "order", "id"]

    def __str__(self):
        return self.text
