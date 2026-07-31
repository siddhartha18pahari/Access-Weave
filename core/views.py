"""
AccessWeave views.

Everything works server-rendered with keyboard-only navigation and no
JavaScript. JavaScript (speech, no-reload card actions, offline) is layered on
top as progressive enhancement — the HTML forms are always the reliable path.
"""
from __future__ import annotations

import json

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_POST

from . import compiler as compiler_mod
from . import ocr as ocr_mod
from . import resources as resources_mod
from .context import get_active_profile
from .models import (AccessProfile, TaskSession, AccessCard, ConsentGrant,
                     AuditEvent, Phrase)
from .passport_schema import validate_payload, default_payload
from .phrases import PHRASE_PACKS
from . import state as state_mod


# --- public pages -----------------------------------------------------------
def home(request):
    resume = None
    if request.user.is_authenticated:
        resume = (TaskSession.objects
                  .filter(owner=request.user)
                  .exclude(status__in=[TaskSession.Status.COMPLETED,
                                       TaskSession.Status.CANCELLED])
                  .order_by("-updated_at").first())
    return render(request, "home.html", {"resume": resume})


def about(request):
    return render(request, "about.html")


def privacy(request):
    return render(request, "privacy.html")


def signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            _seed_new_user(user)
            messages.success(request, "Welcome to AccessWeave.")
            return redirect("onboarding")
    else:
        form = UserCreationForm()
    return render(request, "signup.html", {"form": form})


# --- Access Passport ---------------------------------------------------------
@login_required
def onboarding(request):
    """A short, functional onboarding — no diagnosis, keyboard operable."""
    if request.method == "POST":
        try:
            payload_raw = _payload_from_onboarding(request.POST)
            payload = validate_payload(payload_raw)
        except Exception as exc:
            messages.error(request, f"Please review your choices: {exc}")
            return render(request, "onboarding.html",
                          {"posted": request.POST})
        profile = AccessProfile.objects.create(
            owner=request.user, name=payload["name"], payload=payload,
            is_default=not AccessProfile.objects.filter(owner=request.user).exists(),
        )
        profile.is_default = True
        profile.save()
        AuditEvent.objects.create(owner=request.user, action="profile_created",
                                  detail=profile.name)
        messages.success(request, f"Saved “{profile.name}”. You can change this any time.")
        return redirect("task_new")
    return render(request, "onboarding.html", {"posted": {}})


@login_required
def passport_list(request):
    profiles = AccessProfile.objects.filter(owner=request.user)
    return render(request, "passport_list.html", {"profiles": profiles})


@login_required
@require_POST
def passport_activate(request, pk):
    profile = get_object_or_404(AccessProfile, pk=pk, owner=request.user)
    profile.is_default = True
    profile.save()
    messages.success(request, f"“{profile.name}” is now active.")
    return redirect("passport_list")


@login_required
@require_POST
def passport_delete(request, pk):
    profile = get_object_or_404(AccessProfile, pk=pk, owner=request.user)
    name = profile.name
    profile.delete()
    AuditEvent.objects.create(owner=request.user, action="profile_deleted", detail=name)
    messages.success(request, f"Deleted “{name}”.")
    return redirect("passport_list")


@login_required
@require_POST
def passport_import(request):
    """Import a passport from pasted JSON (validated by the typed schema).

    Accepts either an exported document {"name", "payload", ...} or a bare
    payload dict. Anything malformed is rejected by pydantic — untrusted input
    can never put an unsafe preference set into the interface.
    """
    raw = (request.POST.get("document") or "").strip()
    try:
        data = json.loads(raw)
        payload = data.get("payload", data) if isinstance(data, dict) else None
        payload = validate_payload(payload)
    except Exception:
        messages.error(request, "That doesn't look like a valid Access Passport. "
                                "Please paste the exported JSON exactly.")
        return redirect("passport_list")
    name = (payload.get("name") or "Imported")[:100]
    profile = AccessProfile.objects.create(
        owner=request.user, name=name, payload=payload)
    AuditEvent.objects.create(owner=request.user, action="profile_imported",
                              detail=name)
    messages.success(request, f"Imported “{name}”. You can make it active below.")
    return redirect("passport_list")


@login_required
def passport_export(request, pk):
    """Export the passport as an accessible PDF summary (preferences only)."""
    profile = get_object_or_404(AccessProfile, pk=pk, owner=request.user)
    try:
        from .export import passport_pdf
        pdf = passport_pdf(profile)
    except Exception:
        # Fall back to JSON if reportlab is unavailable.
        payload = {"name": profile.name, "payload": profile.payload,
                   "schema_version": profile.schema_version}
        resp = JsonResponse(payload, json_dumps_params={"indent": 2})
        resp["Content-Disposition"] = f'attachment; filename="access-passport-{profile.pk}.json"'
        return resp
    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="access-passport-{profile.pk}.pdf"'
    AuditEvent.objects.create(owner=request.user, action="profile_exported", detail=profile.name)
    return resp


# --- Tasks: create, compile, play -------------------------------------------
@login_required
def task_new(request):
    if request.method == "POST":
        goal = (request.POST.get("goal") or "").strip()
        source_type = request.POST.get("source_type") or "text"
        source_text = (request.POST.get("source_text") or "").strip()
        no_storage = request.POST.get("no_storage") == "on"
        is_routine = request.POST.get("is_routine") == "on"
        ocr_conf = None

        # Optional URL -> fetch and strip to readable text (SSRF-guarded).
        page_url = (request.POST.get("page_url") or "").strip()
        if page_url and not source_text:
            from . import webreader
            try:
                title, page_text = webreader.fetch(page_url)
                source_text = page_text
                source_type = "webpage"
                if title and not goal:
                    goal = f"Understand: {title}"
                messages.info(request, "I read that page and removed the menus, "
                                       "adverts, and scripts.")
            except webreader.FetchError as exc:
                messages.error(request, str(exc))
                return render(request, "task_new.html",
                              {"posted": request.POST,
                               "ocr_available": ocr_mod.ocr_available()})

        # Optional image -> OCR (processed in memory, never stored by default).
        upload = request.FILES.get("image")
        ocr_message = ""
        if upload is not None:
            data = upload.read()
            quality = ocr_mod.image_quality_report(data)
            result = ocr_mod.extract_text(data)
            if result["available"] and result["text"]:
                source_text = result["text"]
                source_type = "image"
                ocr_conf = result["confidence"]
                for note in quality.get("notes", []):
                    messages.info(request, note)
            else:
                ocr_message = result["message"]
            del data  # discard bytes

        if not goal and not source_text:
            messages.error(request, "Tell me your goal, or paste some text to work on.")
            return render(request, "task_new.html",
                          {"posted": request.POST, "ocr_message": ocr_message,
                           "ocr_available": ocr_mod.ocr_available()})

        profile = get_active_profile(request)
        payload = profile.payload if profile else default_payload()

        result = compiler_mod.compile_task(
            goal=goal or "Make this accessible", source_text=source_text,
            source_type=source_type, passport=payload, ocr_confidence=ocr_conf)

        # Enforce the accessibility contract at runtime, not just in tests:
        # store the report with the task and surface any failure to the user.
        result["analysis"]["validation"] = result["validation"]
        if not result["validation"]["passed"]:
            AuditEvent.objects.create(
                owner=request.user, action="validation_failed",
                detail=", ".join(result["validation"]["errors"])[:200])
            messages.warning(
                request,
                "Heads up: this task didn't pass every accessibility check "
                f"({', '.join(result['validation']['errors'])}). "
                "Please double-check the steps against the original.")

        session = TaskSession.objects.create(
            owner=request.user, goal=goal or "Make this accessible",
            source_type="routine" if is_routine else source_type,
            active_profile=profile,
            source_text="" if no_storage else source_text,
            analysis=result["analysis"], task_graph=result["task_graph"],
            no_storage=no_storage, status=TaskSession.Status.READY,
            retention_policy="keep" if is_routine else "delete_on_completion",
        )
        for card in result["cards"]:
            AccessCard.objects.create(
                session=session, sequence=card["sequence"],
                card_type=card["type"], payload=card,
                confidence=card.get("confidence"),
                requires_confirmation=card.get("requires_confirmation", False),
            )
        AuditEvent.objects.create(owner=request.user, action="task_created",
                                  detail=session.goal[:60])
        return redirect("task_player", pk=session.pk)

    return render(request, "task_new.html",
                  {"posted": {}, "ocr_available": ocr_mod.ocr_available()})


@login_required
def task_player(request, pk):
    session = _owned_task(request, pk)
    cards = list(session.cards.all())
    if not cards:
        messages.error(request, "This task has no steps.")
        return redirect("task_new")
    try:
        step = int(request.GET.get("step", session.current_step))
    except (TypeError, ValueError):
        step = session.current_step
    step = max(0, min(step, len(cards) - 1))
    if session.status == TaskSession.Status.READY:
        state_mod.transition(session, TaskSession.Status.IN_PROGRESS)
    # Persist the resume point only when it actually changed (keeps repeated
    # GETs / prefetches from writing on every view).
    if session.current_step != step:
        session.current_step = step
        session.save(update_fields=["current_step", "updated_at"])

    current = cards[step]
    current_payload = current.payload
    if request.GET.get("simplify"):
        from .cards import simplify_text
        current_payload = dict(current_payload)
        content = dict(current_payload.get("content", {}))
        if content.get("plain_text"):
            content["plain_text"] = simplify_text(content["plain_text"])
        current_payload["content"] = content
    return render(request, "task_player.html", {
        "session": session,
        "cards": cards,
        "current": current,
        "current_payload": current_payload,
        "step": step,
        "total": len(cards),
        "progress_pct": round((step + 1) / len(cards) * 100),
        "prev_step": step - 1 if step > 0 else None,
        "next_step": step + 1 if step < len(cards) - 1 else None,
    })


@login_required
def task_analysis(request, pk):
    session = _owned_task(request, pk)
    return render(request, "task_analysis.html", {
        "session": session,
        "analysis": session.analysis,
        "graph": session.task_graph,
        "validation_cards": [c.payload for c in session.cards.all()],
    })


@login_required
@require_POST
def task_action(request, pk):
    """Card/task actions. Returns JSON for JS, or redirects for no-JS."""
    session = _owned_task(request, pk)
    action = request.POST.get("action")
    wants_json = request.headers.get("x-requested-with") == "fetch"

    if action == "complete_step":
        cards = list(session.cards.all())
        step = min(session.current_step + 1, len(cards) - 1)
        session.current_step = step
        session.save(update_fields=["current_step", "updated_at"])
        if step == len(cards) - 1:
            _complete_task(session)
        if wants_json:
            return JsonResponse({"ok": True, "step": step})
        return redirect(f"{reverse('task_player', args=[pk])}?step={step}")

    if action == "complete_task":
        _complete_task(session)
        if wants_json:
            return JsonResponse({"ok": True, "status": session.status})
        messages.success(request, "Task completed.")
        return redirect("task_player", pk=pk)

    if action in {"pause", "cancel"}:
        target = (TaskSession.Status.WAITING_FOR_USER if action == "pause"
                  else TaskSession.Status.CANCELLED)
        try:
            state_mod.transition(session, target)
        except state_mod.InvalidTransition:
            pass
        if wants_json:
            return JsonResponse({"ok": True, "status": session.status})
        return redirect("task_player", pk=pk)

    if action == "feedback":
        helpful = request.POST.get("helpful")
        AuditEvent.objects.create(owner=request.user, action="feedback",
                                  detail=f"helpful={helpful}")
        if wants_json:
            return JsonResponse({"ok": True})
        messages.success(request, "Thanks — your feedback helps improve your profile, not a diagnosis.")
        return redirect("task_player", pk=pk)

    return JsonResponse({"ok": False, "error": "unknown_action"}, status=400)


@login_required
@require_POST
def task_repeat(request, pk):
    """Restart a saved routine from step one (keeps the compiled steps)."""
    session = _owned_task(request, pk)
    session.current_step = 0
    session.completed_at = None
    session.status = TaskSession.Status.READY
    session.save(update_fields=["current_step", "completed_at", "status", "updated_at"])
    AuditEvent.objects.create(owner=request.user, action="routine_repeated",
                              detail=session.goal[:60])
    return redirect("task_player", pk=pk)


@login_required
@require_POST
def task_delete(request, pk):
    session = _owned_task(request, pk)
    session.delete()  # cascades cards; source text goes with it
    AuditEvent.objects.create(owner=request.user, action="task_deleted")
    messages.success(request, "Task and its source were deleted.")
    return redirect("task_list")


@login_required
def task_list(request):
    tasks = TaskSession.objects.filter(owner=request.user)
    return render(request, "task_list.html", {"tasks": tasks})


# --- Communication Bridge ----------------------------------------------------
@login_required
def look(request):
    """Live 'Look around' — on-device camera object detection with speech."""
    return render(request, "look.html")


@login_required
def soundwatch(request):
    """Sound Watch — visual + vibration alerts for sounds (on-device)."""
    return render(request, "soundwatch.html")


@login_required
def captions(request):
    """Conversation Mode — live captions + spoken replies."""
    return render(request, "captions.html")


@login_required
def communication(request):
    packs = {}
    for pack, items in PHRASE_PACKS.items():
        packs[pack] = [{"text": t, "symbol": s} for t, s in items]
    custom = list(request.user.phrases.all().values("id", "text", "symbol", "pack"))
    return render(request, "communication.html", {"packs": packs, "custom": custom})


@login_required
@require_POST
def phrase_add(request):
    text = (request.POST.get("text") or "").strip()
    if text:
        Phrase.objects.create(owner=request.user, text=text[:200],
                              symbol=(request.POST.get("symbol") or "")[:8],
                              pack="custom")
        messages.success(request, "Phrase saved.")
    return redirect("communication")


@login_required
@require_POST
def phrase_delete(request, pk):
    Phrase.objects.filter(pk=pk, owner=request.user).delete()
    return redirect("communication")


# --- Resource Matcher --------------------------------------------------------
@login_required
def resources(request):
    result = None
    goal = ""
    if request.method == "POST":
        goal = (request.POST.get("goal") or "").strip()
        barrier_list = request.POST.getlist("barriers")
        affordability = request.POST.get("affordability") == "on"
        result = resources_mod.match(goal, barrier_list,
                                     affordability_pressure=affordability)
    return render(request, "resources.html", {
        "result": result, "goal": goal,
        "taxonomy": resources_mod._POPULATION_WEIGHT,
    })


# --- Population dashboard (self-contained aggregate) -------------------------
@login_required
def dashboard(request):
    from .resources import _POPULATION_WEIGHT, VERIFIED_ON
    rows = sorted(_POPULATION_WEIGHT.items(), key=lambda x: -x[1])
    return render(request, "dashboard.html", {
        "rows": [{"category": k, "weight": round(v * 100)} for k, v in rows],
        "verified_on": VERIFIED_ON,
        "min_group": 10,
    })


# --- account / privacy actions ----------------------------------------------
@login_required
def recent_summary(request):
    """A short spoken-friendly recap of recent tasks (for voice 'what have I done')."""
    tasks = list(TaskSession.objects.filter(owner=request.user)[:5])
    if not tasks:
        return JsonResponse({"summary": "You have no tasks yet. Say new task to start one."})
    parts = [f"You have {len(tasks)} recent task{'s' if len(tasks) != 1 else ''}."]
    for t in tasks:
        parts.append(f"{t.goal}, {t.get_status_display().lower()}.")
    return JsonResponse({"summary": " ".join(parts)})


@login_required
@require_POST
def tts_speak(request):
    """Proxy short text to ElevenLabs and return MP3 audio.

    Returns 204 (no content) when TTS isn't configured or fails, which tells the
    browser to use its built-in speech synthesis instead. The API key never
    leaves the server.
    """
    from . import tts as tts_mod
    if not tts_mod.is_enabled():
        return HttpResponse(status=204)
    text = (request.POST.get("text") or "")[:tts_mod.MAX_CHARS]
    audio = tts_mod.synthesize(text)
    if not audio:
        return HttpResponse(status=204)
    resp = HttpResponse(audio, content_type="audio/mpeg")
    resp["Cache-Control"] = "no-store"
    return resp


@login_required
@require_POST
def delete_all_data(request):
    """One-click deletion of all task data for this user (privacy control)."""
    TaskSession.objects.filter(owner=request.user).delete()
    AuditEvent.objects.create(owner=request.user, action="bulk_delete_tasks")
    messages.success(request, "All your tasks and their sources were deleted.")
    return redirect("privacy")


# --- helpers ----------------------------------------------------------------
def _owned_task(request, pk) -> TaskSession:
    session = get_object_or_404(TaskSession, pk=pk)
    if session.owner_id != request.user.id:
        raise PermissionDenied
    return session


def _complete_task(session):
    try:
        state_mod.transition(session, TaskSession.Status.COMPLETED)
    except state_mod.InvalidTransition:
        pass
    if session.retention_policy == "delete_on_completion" or session.no_storage:
        session.purge_source()


def _num(raw, default, cast):
    """Parse a numeric form value defensively (bad input -> default, not a 500)."""
    try:
        return cast(raw)
    except (TypeError, ValueError):
        return default


def _payload_from_onboarding(post) -> dict:
    input_modes = post.getlist("input_modes") or ["keyboard"]
    return {
        "name": (post.get("name") or "My profile").strip()[:100],
        "input_modes": input_modes,
        "minimum_target_px": _num(post.get("minimum_target_px"), 44, int),
        "output": {
            "text_scale": _num(post.get("text_scale"), 1.0, float),
            "contrast": post.get("contrast") or "system",
            "speech_enabled": post.get("speech_enabled") == "on",
            "captions": post.get("captions") == "on",
            "reduced_motion": post.get("reduced_motion") == "on",
            "symbols_with_text": post.get("symbols_with_text") == "on",
            "reading_ruler": post.get("reading_ruler") == "on",
        },
        "cognitive": {
            "plain_language": post.get("plain_language") == "on",
            "one_step_at_a_time": post.get("one_step_at_a_time") == "on",
            "show_progress": post.get("show_progress", "on") == "on",
            "recovery_instructions": post.get("recovery_instructions", "on") == "on",
            "reduced_choice_mode": post.get("reduced_choice_mode") == "on",
        },
        "privacy": {
            "store_images": False,
            "store_transcripts": False,
            "location_policy": "off",
            "supporter_access": post.get("supporter_access") == "on",
        },
        "safety": {
            "external_action": post.get("external_action") or "strong",
            "financial_action": post.get("financial_action") or "strong",
            "medical_action": "block",
            "legal_action": "strong",
        },
    }


def _seed_new_user(user: User):
    """Give a new account two starter passports so the demo is immediate."""
    AccessProfile.objects.create(
        owner=user, name="Regular", is_default=True,
        payload={**default_payload("Regular"),
                 "output": {"text_scale": 1.0, "contrast": "system",
                            "speech_enabled": True, "captions": True,
                            "reduced_motion": False, "symbols_with_text": False,
                            "reading_ruler": False, "speech_rate": 1.0}})
    AccessProfile.objects.create(
        owner=user, name="Low-energy",
        payload={**default_payload("Low-energy"),
                 "output": {"text_scale": 1.6, "contrast": "high",
                            "speech_enabled": True, "captions": True,
                            "reduced_motion": True, "symbols_with_text": True,
                            "reading_ruler": True, "speech_rate": 0.9},
                 "cognitive": {"plain_language": True, "one_step_at_a_time": True,
                               "show_progress": True, "recovery_instructions": True,
                               "reduced_choice_mode": True}})
