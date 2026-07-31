"""Unit tests for the deterministic accessibility engine (no DB needed)."""
from django.test import SimpleTestCase

from core.barriers import detect_barriers, merge_model_barriers, VALID_CATEGORIES
from core.cards import simplify_text, validate_cards, make_card
from core.compiler import compile_task, classify_source, reading_level
from core.passport_schema import validate_payload, default_payload
from core.safety import required_confirmation, classify_action
from core import resources


MED = ("Take one capsule twice daily with food. Do not exceed two capsules in "
       "24 hours. Contact your pharmacist if dizziness persists.")


class BarrierTests(SimpleTestCase):
    def test_safety_value_detected_and_flagged(self):
        barriers = detect_barriers(MED)
        cats = {b.category for b in barriers}
        self.assertIn("safety", cats)
        safety = [b for b in barriers if b.category == "safety"]
        self.assertTrue(any(b.requires_user_verification for b in safety))

    def test_dense_language_detected(self):
        text = ("Applicants shall, pursuant to the aforementioned provisions and "
                "notwithstanding any prior submission, ensure compliance herewith.")
        cats = {b.category for b in detect_barriers(text)}
        self.assertIn("cognition", cats)

    def test_model_barriers_reject_unknown_category(self):
        merged = merge_model_barriers([], [{"category": "not_real", "title": "x"}])
        self.assertEqual(merged, [])
        merged = merge_model_barriers([], [{"category": "cognition", "title": "ok"}])
        self.assertEqual(len(merged), 1)

    def test_taxonomy_is_closed_set(self):
        self.assertIn("safety", VALID_CATEGORIES)
        self.assertNotIn("banana", VALID_CATEGORIES)


class SafetyPolicyTests(SimpleTestCase):
    def test_medical_action_always_blocked(self):
        # Even if a passport tried to weaken it, the floor blocks medical.
        p = {"safety": {"medical_action": "standard"}}
        self.assertEqual(required_confirmation("medical", p), "block")

    def test_passport_can_strengthen_but_not_weaken(self):
        # Platform floor for external is "strong"; a weaker pref cannot lower it.
        p = {"safety": {"external_action": "standard"}}
        self.assertEqual(required_confirmation("external", p), "strong")

    def test_classify_action(self):
        self.assertEqual(classify_action("submit this form"), "external")
        self.assertEqual(classify_action("pay the $20 fee"), "financial")
        self.assertEqual(classify_action("change the dose"), "medical")


class SimplifyTests(SimpleTestCase):
    def test_simplify_swaps_hard_words(self):
        out = simplify_text("You shall utilize the form prior to submission.")
        self.assertIn("must", out.lower())
        self.assertIn("use", out.lower())
        self.assertIn("before", out.lower())

    def test_simplify_preserves_numbers(self):
        out = simplify_text("Do not exceed 2 capsules in 24 hours.")
        self.assertIn("2", out)
        self.assertIn("24", out)


class CompilerTests(SimpleTestCase):
    def test_medicine_produces_verbatim_warning(self):
        r = compile_task(goal="Read label", source_text=MED, passport=default_payload())
        types = [c["type"] for c in r["cards"]]
        self.assertEqual(r["analysis"]["kind"], "medicine")
        self.assertIn("warning", types)
        warning = next(c for c in r["cards"] if c["type"] == "warning")
        self.assertIn("two capsules", warning["content"]["plain_text"])
        self.assertTrue(warning["provenance"].get("verbatim"))

    def test_every_task_has_summary_and_completion(self):
        r = compile_task(goal="Anything", source_text="", passport=default_payload())
        types = [c["type"] for c in r["cards"]]
        self.assertEqual(types[0], "summary")
        self.assertEqual(types[-1], "completion")

    def test_compiled_cards_pass_accessibility_contract(self):
        for text in [MED, "First name: __ Social security number: __ Signature: __", ""]:
            r = compile_task(goal="Task", source_text=text, passport=default_payload())
            self.assertTrue(r["validation"]["passed"],
                            msg=f"failed for {text!r}: {r['validation']['errors']}")

    def test_form_flags_sensitive_field(self):
        r = compile_task(goal="Apply",
                         source_text="First name: __\nSocial security number: __\nSignature: __",
                         passport=default_payload())
        self.assertEqual(r["analysis"]["kind"], "form")
        # a confirmation before submit must exist and require confirmation
        conf = [c for c in r["cards"] if c["type"] == "confirmation"]
        self.assertTrue(conf and conf[0]["requires_confirmation"])

    def test_classify_source(self):
        self.assertEqual(classify_source(MED, "read label"), "medicine")
        self.assertEqual(classify_source("", "renew my transit pass"), "goal_only")

    def test_bill_extracts_amount_and_due(self):
        bill = ("ACME Electric. Invoice #4471. Amount due: $84.20. "
                "Due date: 03/15/2026. Account number: 99812.")
        r = compile_task(goal="pay my bill", source_text=bill, passport=default_payload())
        self.assertEqual(r["analysis"]["kind"], "bill")
        info = next(c for c in r["cards"] if c["type"] == "information")
        self.assertIn("$84.20", str(info["content"]["structured_values"]))
        # paying is a financial action: a confirmation card must be present
        self.assertTrue(any(c["type"] == "confirmation" and c["requires_confirmation"]
                            for c in r["cards"]))
        self.assertTrue(r["validation"]["passed"])

    def test_appointment_extracts_and_adds_communication(self):
        appt = ("Your appointment is scheduled for Tuesday, March 10 at 2:30pm at "
                "Riverside Clinic. Please arrive 15 minutes early and bring your referral.")
        r = compile_task(goal="", source_text=appt, passport=default_payload())
        self.assertEqual(r["analysis"]["kind"], "appointment")
        self.assertIn("communication", [c["type"] for c in r["cards"]])
        self.assertTrue(r["validation"]["passed"])

    def test_more_goal_templates(self):
        from core.compiler import goal_template
        self.assertGreaterEqual(len(goal_template("help me cook dinner")), 3)
        self.assertGreaterEqual(len(goal_template("write an email")), 3)
        self.assertGreaterEqual(len(goal_template("set up voice control")), 3)

    def test_bare_maximum_phrasing_gets_verbatim_warning(self):
        # Regression: "Maximum 4 capsules" (no "of") must still produce the
        # dedicated verbatim limit card — a safety-critical path.
        for text in ("Take one capsule daily. Maximum 4 capsules in 24 hours.",
                     "Take one tablet daily. Maximum dose is 8 tablets per day.",
                     "Take one pill daily. Do not exceed two pills in 24 hours."):
            r = compile_task(goal="Read label", source_text=text,
                             passport=default_payload())
            types = [c["type"] for c in r["cards"]]
            self.assertIn("warning", types, msg=f"no warning card for: {text!r}")

    def test_reading_level_is_positive_for_dense_text(self):
        self.assertGreater(reading_level(MED), 0)


class ValidatorTests(SimpleTestCase):
    def test_unconfirmed_consequential_action_fails(self):
        bad = make_card("instruction", "Send it", body="x", actions=["submit"],
                        requires_confirmation=False)
        report = validate_cards([bad], passport=default_payload())
        self.assertFalse(report["passed"])

    def test_low_confidence_must_be_marked(self):
        risky = make_card("information", "Maybe", body="x", confidence=0.4)
        report = validate_cards([risky])
        self.assertFalse(report["passed"])
        risky2 = make_card("information", "Maybe", body="x", confidence=0.4,
                           provenance={"uncertain": True})
        self.assertTrue(validate_cards([risky2])["passed"])


class PassportSchemaTests(SimpleTestCase):
    def test_default_is_valid(self):
        self.assertEqual(validate_payload(default_payload())["name"], "My profile")

    def test_text_scale_bounds_enforced(self):
        with self.assertRaises(Exception):
            validate_payload({"name": "x", "output": {"text_scale": 9.0}})

    def test_at_least_one_input_mode(self):
        with self.assertRaises(Exception):
            validate_payload({"name": "x", "input_modes": []})


class WebReaderTests(SimpleTestCase):
    """The URL reader takes user-supplied addresses, so its guards are tested."""

    def test_rejects_non_http_schemes(self):
        from core import webreader
        for bad in ("file:///etc/passwd", "ftp://example.com", "gopher://x"):
            with self.assertRaises(webreader.FetchError):
                webreader.fetch(bad)

    def test_ip_blocklist_covers_known_ssrf_targets(self):
        """Regression: every one of these must be refused before connecting."""
        import ipaddress
        from core.webreader import _ip_is_blocked
        must_block = [
            "127.0.0.1", "10.0.0.5", "192.168.1.1", "172.16.0.1",
            "169.254.169.254",          # cloud metadata
            "0.0.0.0", "::", "::1", "fd00::1", "fe80::1",
            "::ffff:127.0.0.1",         # IPv4-mapped loopback
            "::ffff:169.254.169.254",   # IPv4-mapped metadata
            "100.64.0.1",               # RFC 6598 CGNAT
            "198.18.0.1",               # RFC 2544 benchmarking
            "192.0.0.1",                # IETF protocol assignments
        ]
        for ip in must_block:
            self.assertTrue(_ip_is_blocked(ipaddress.ip_address(ip)),
                            msg=f"{ip} should be blocked")
        for ip in ["93.184.216.34", "8.8.8.8", "2606:4700:4700::1111"]:
            self.assertFalse(_ip_is_blocked(ipaddress.ip_address(ip)),
                             msg=f"{ip} should be allowed")

    def test_rejects_loopback_and_private_hosts(self):
        from core import webreader
        for bad in ("http://127.0.0.1/", "http://localhost:8000/admin/",
                    "http://169.254.169.254/latest/meta-data/",
                    "http://10.0.0.5/", "http://192.168.1.1/"):
            with self.assertRaises(webreader.FetchError):
                webreader.fetch(bad)

    def test_extract_strips_scripts_and_nav(self):
        from core.webreader import extract
        title, text = extract(
            "<html><head><title>Renew your pass</title></head><body>"
            "<nav>Home About Contact</nav>"
            "<script>alert('x')</script><style>.a{}</style>"
            "<main><h1>Renew</h1><p>Bring your ID card.</p>"
            "<p>Pay the fee of $20.</p></main>"
            "<footer>Cookie notice</footer></body></html>")
        self.assertEqual(title, "Renew your pass")
        self.assertIn("Bring your ID card.", text)
        self.assertIn("$20", text)
        for gone in ("alert", "Cookie notice", "About Contact", ".a{}"):
            self.assertNotIn(gone, text)

    def test_extract_raises_when_no_readable_text(self):
        from core import webreader
        with self.assertRaises(webreader.FetchError):
            webreader.extract("<html><body><script>var a=1</script></body></html>")

    def test_extracted_page_compiles_into_cards(self):
        from core.webreader import extract
        _, text = extract("<html><title>Form</title><body><main>"
                          "<p>Applicants shall submit prior to the deadline.</p>"
                          "<p>First name: ___</p><p>Signature: ___</p>"
                          "</main></body></html>")
        r = compile_task(goal="Understand this page", source_text=text,
                         source_type="webpage", passport=default_payload())
        self.assertTrue(r["validation"]["passed"])
        self.assertGreaterEqual(len(r["cards"]), 3)


class ResourceTests(SimpleTestCase):
    def test_low_cost_first(self):
        r = resources.match("use phone with less hand movement", ["operation"])
        self.assertTrue(r["recommendations"])
        self.assertEqual(r["recommendations"][0]["cost_band"], "free")

    def test_disclaimer_present(self):
        r = resources.match("read", ["perception"])
        self.assertIn("not medical advice", r["disclaimer"])
