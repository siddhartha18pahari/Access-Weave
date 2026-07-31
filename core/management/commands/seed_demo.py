"""
Seed (or reset) a clearly-marked demo account and one sample task.

    python manage.py seed_demo          # create demo user + sample task
    python manage.py seed_demo --reset  # wipe demo user's data first

Demo credentials: demo / accessweave
"""
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from core.compiler import compile_task
from core.models import AccessProfile, TaskSession, AccessCard
from core.passport_schema import default_payload

DEMO_USERNAME = "demo"
DEMO_PASSWORD = "accessweave"

SAMPLE_LABEL = (
    "Take one capsule twice daily with food. "
    "Do not exceed two capsules in 24 hours. "
    "Contact your pharmacist if dizziness persists."
)


class Command(BaseCommand):
    help = "Create a clearly-marked demo account with a sample task."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true",
                            help="Delete the demo user's data first.")

    def handle(self, *args, **opts):
        user, created = User.objects.get_or_create(
            username=DEMO_USERNAME,
            defaults={"first_name": "Demo", "email": "demo@example.com"})
        user.set_password(DEMO_PASSWORD)
        user.save()

        if opts["reset"]:
            TaskSession.objects.filter(owner=user).delete()
            AccessProfile.objects.filter(owner=user).delete()
            self.stdout.write("Reset demo data.")

        if not AccessProfile.objects.filter(owner=user).exists():
            AccessProfile.objects.create(
                owner=user, name="Regular", is_default=True,
                payload={**default_payload("Regular"),
                         "output": {"text_scale": 1.0, "contrast": "system",
                                    "speech_enabled": True, "captions": True,
                                    "reduced_motion": False, "speech_rate": 1.0,
                                    "symbols_with_text": False, "reading_ruler": False}})
            AccessProfile.objects.create(
                owner=user, name="Low-energy",
                payload={**default_payload("Low-energy"),
                         "output": {"text_scale": 1.6, "contrast": "high",
                                    "speech_enabled": True, "captions": True,
                                    "reduced_motion": True, "speech_rate": 0.9,
                                    "symbols_with_text": True, "reading_ruler": True},
                         "cognitive": {"plain_language": True,
                                       "one_step_at_a_time": True,
                                       "show_progress": True,
                                       "recovery_instructions": True,
                                       "reduced_choice_mode": True}})

        profile = AccessProfile.objects.filter(owner=user, is_default=True).first()

        if not TaskSession.objects.filter(owner=user).exists():
            result = compile_task(
                goal="Read my medicine label", source_text=SAMPLE_LABEL,
                source_type="text", passport=profile.payload)
            session = TaskSession.objects.create(
                owner=user, goal="Read my medicine label", source_type="text",
                active_profile=profile, source_text=SAMPLE_LABEL,
                analysis=result["analysis"], task_graph=result["task_graph"],
                status=TaskSession.Status.READY)
            for card in result["cards"]:
                AccessCard.objects.create(
                    session=session, sequence=card["sequence"],
                    card_type=card["type"], payload=card,
                    confidence=card.get("confidence"),
                    requires_confirmation=card.get("requires_confirmation", False))

        self.stdout.write(self.style.SUCCESS(
            f"Demo ready. Login: {DEMO_USERNAME} / {DEMO_PASSWORD}"))
