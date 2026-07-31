"""Template context processor: expose the active Access Passport everywhere."""
from django.conf import settings

from .passport_schema import default_payload


def get_active_profile(request):
    """Return the user's active AccessProfile, or None."""
    if not request.user.is_authenticated:
        return None
    from .models import AccessProfile

    profile = (
        AccessProfile.objects.filter(owner=request.user, is_default=True).first()
        or AccessProfile.objects.filter(owner=request.user).first()
    )
    return profile


def accessweave_context(request):
    profile = get_active_profile(request)
    payload = profile.payload if profile else default_payload("Default")
    return {
        "active_profile": profile,
        "active_payload": payload,
        "aw_flags": settings.ACCESSWEAVE,
        "aw_tts_enabled": bool(settings.ACCESSWEAVE.get("ELEVENLABS_API_KEY")),
        "aw_v": settings.AW_STATIC_VERSION,
    }
