"""Integration tests: ownership, state machine, deletion, privacy."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from core.models import TaskSession, AccessCard, AccessProfile
from core.compiler import compile_task
from core.passport_schema import default_payload
from core import state


def _make_task(owner, goal="Task", text="Take one capsule twice daily. Do not exceed two capsules in 24 hours."):
    r = compile_task(goal=goal, source_text=text, passport=default_payload())
    s = TaskSession.objects.create(owner=owner, goal=goal, source_text=text,
                                   analysis=r["analysis"], task_graph=r["task_graph"],
                                   status=TaskSession.Status.READY)
    for c in r["cards"]:
        AccessCard.objects.create(session=s, sequence=c["sequence"],
                                  card_type=c["type"], payload=c,
                                  requires_confirmation=c.get("requires_confirmation", False))
    return s


class OwnershipTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice", password="pw12345678")
        self.bob = User.objects.create_user("bob", password="pw12345678")
        self.task = _make_task(self.alice)

    def test_owner_can_view(self):
        self.client.force_login(self.alice)
        resp = self.client.get(reverse("task_player", args=[self.task.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_non_owner_forbidden(self):
        self.client.force_login(self.bob)
        resp = self.client.get(reverse("task_player", args=[self.task.pk]))
        self.assertEqual(resp.status_code, 403)

    def test_anonymous_redirected_to_login(self):
        resp = self.client.get(reverse("task_player", args=[self.task.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login/", resp["Location"])


class DeletionTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice", password="pw12345678")
        self.task = _make_task(self.alice)

    def test_delete_removes_task_and_cards(self):
        self.client.force_login(self.alice)
        self.client.post(reverse("task_delete", args=[self.task.pk]))
        self.assertFalse(TaskSession.objects.filter(pk=self.task.pk).exists())
        self.assertFalse(AccessCard.objects.filter(session_id=self.task.pk).exists())

    def test_completion_purges_source(self):
        self.task.retention_policy = "delete_on_completion"
        self.task.save()
        state.transition(self.task, TaskSession.Status.IN_PROGRESS)
        from core.views import _complete_task
        _complete_task(self.task)
        self.task.refresh_from_db()
        self.assertEqual(self.task.source_text, "")
        self.assertEqual(self.task.status, TaskSession.Status.COMPLETED)

    def test_delete_all_data(self):
        self.client.force_login(self.alice)
        _make_task(self.alice, goal="Second")
        self.client.post(reverse("delete_all_data"))
        self.assertEqual(TaskSession.objects.filter(owner=self.alice).count(), 0)


class StateMachineTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice", password="pw12345678")
        self.task = _make_task(self.alice)

    def test_valid_transition(self):
        state.transition(self.task, TaskSession.Status.IN_PROGRESS)
        self.assertEqual(self.task.status, TaskSession.Status.IN_PROGRESS)

    def test_invalid_transition_raises(self):
        state.transition(self.task, TaskSession.Status.IN_PROGRESS)
        state.transition(self.task, TaskSession.Status.COMPLETED)
        with self.assertRaises(state.InvalidTransition):
            state.transition(self.task, TaskSession.Status.IN_PROGRESS)


class ProfileTests(TestCase):
    def test_only_one_default_profile(self):
        u = User.objects.create_user("u", password="pw12345678")
        p1 = AccessProfile.objects.create(owner=u, name="A", is_default=True,
                                          payload=default_payload("A"))
        p2 = AccessProfile.objects.create(owner=u, name="B", is_default=True,
                                          payload=default_payload("B"))
        p1.refresh_from_db()
        self.assertFalse(p1.is_default)
        self.assertTrue(p2.is_default)

    def test_task_creation_flow(self):
        u = User.objects.create_user("u", password="pw12345678")
        self.client.force_login(u)
        resp = self.client.post(reverse("task_new"), {
            "goal": "Read my medicine label",
            "source_text": "Take one capsule twice daily with food. Do not exceed two capsules in 24 hours.",
            "source_type": "text",
        })
        self.assertEqual(resp.status_code, 302)
        task = TaskSession.objects.filter(owner=u).first()
        self.assertIsNotNone(task)
        self.assertGreaterEqual(task.cards.count(), 4)

    def test_no_storage_mode_erases_source(self):
        u = User.objects.create_user("u", password="pw12345678")
        self.client.force_login(u)
        self.client.post(reverse("task_new"), {
            "goal": "Sensitive", "source_text": "secret text here for the task",
            "source_type": "text", "no_storage": "on"})
        task = TaskSession.objects.filter(owner=u).first()
        self.assertEqual(task.source_text, "")


class NewFeatureTests(TestCase):
    def setUp(self):
        self.u = User.objects.create_user("u", password="pw12345678")
        self.client.force_login(self.u)

    def test_onboarding_bad_numeric_input_does_not_500(self):
        resp = self.client.post(reverse("onboarding"), {
            "name": "X", "input_modes": "keyboard",
            "minimum_target_px": "not-a-number", "text_scale": "huge"})
        self.assertIn(resp.status_code, (200, 302))  # graceful, never a 500

    def test_passport_import_valid(self):
        from core.passport_schema import default_payload
        import json as _json
        doc = _json.dumps({"name": "Travel", "payload": default_payload("Travel")})
        resp = self.client.post(reverse("passport_import"), {"document": doc})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(AccessProfile.objects.filter(owner=self.u, name="Travel").exists())

    def test_passport_import_rejects_garbage(self):
        for bad in ("not json", '{"payload": {"output": {"text_scale": 99}}}'):
            self.client.post(reverse("passport_import"), {"document": bad})
        self.assertEqual(AccessProfile.objects.filter(owner=self.u).count(), 0)

    def test_routine_creation_and_repeat(self):
        self.client.post(reverse("task_new"), {
            "goal": "Morning routine",
            "source_text": "1. Take meds\n2. Eat breakfast\n3. Pack bag",
            "source_type": "text", "is_routine": "on"})
        task = TaskSession.objects.get(owner=self.u)
        self.assertEqual(task.source_type, "routine")
        self.assertEqual(task.retention_policy, "keep")
        # complete it, then repeat resets to the start
        task.status = TaskSession.Status.COMPLETED
        task.current_step = 4
        task.save()
        resp = self.client.post(reverse("task_repeat", args=[task.pk]))
        self.assertEqual(resp.status_code, 302)
        task.refresh_from_db()
        self.assertEqual(task.current_step, 0)
        self.assertEqual(task.status, TaskSession.Status.READY)

    def test_new_pages_render(self):
        for name in ("look", "soundwatch", "captions"):
            resp = self.client.get(reverse(name))
            self.assertEqual(resp.status_code, 200, msg=name)

    def test_task_player_get_is_idempotent_for_current_step(self):
        task = _make_task(self.u)
        self.client.get(reverse("task_player", args=[task.pk]) + "?step=1")
        task.refresh_from_db()
        first_updated = task.updated_at
        self.client.get(reverse("task_player", args=[task.pk]) + "?step=1")
        task.refresh_from_db()
        self.assertEqual(task.updated_at, first_updated)  # no write on repeat GET
