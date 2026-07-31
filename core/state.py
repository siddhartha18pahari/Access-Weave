"""Task state machine. Only valid transitions are allowed."""
from .models import TaskSession, AuditEvent

S = TaskSession.Status

ALLOWED = {
    S.NOT_STARTED: {S.ANALYZING, S.CANCELLED},
    S.ANALYZING: {S.READY, S.BLOCKED, S.CANCELLED},
    S.READY: {S.IN_PROGRESS, S.CANCELLED},
    S.IN_PROGRESS: {S.WAITING_FOR_USER, S.BLOCKED, S.NEEDS_SUPPORT,
                    S.COMPLETED, S.CANCELLED},
    S.WAITING_FOR_USER: {S.IN_PROGRESS, S.COMPLETED, S.CANCELLED},
    S.BLOCKED: {S.IN_PROGRESS, S.NEEDS_SUPPORT, S.CANCELLED},
    S.NEEDS_SUPPORT: {S.IN_PROGRESS, S.CANCELLED},
    S.COMPLETED: set(),
    S.CANCELLED: set(),
}


class InvalidTransition(Exception):
    pass


def transition(session: TaskSession, to_status: str, *, audit: bool = True) -> TaskSession:
    current = session.status
    if to_status == current:
        return session
    if to_status not in ALLOWED.get(current, set()):
        raise InvalidTransition(f"Cannot move from {current} to {to_status}.")
    session.status = to_status
    if to_status == S.COMPLETED:
        from django.utils import timezone
        session.completed_at = timezone.now()
    session.save(update_fields=["status", "completed_at", "updated_at"])
    if audit:
        AuditEvent.objects.create(
            owner=session.owner, action="task_transition",
            detail=f"{current} -> {to_status}")
    return session
