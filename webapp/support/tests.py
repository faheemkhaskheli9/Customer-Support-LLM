"""End-to-end checks for the evolving web app, without paid model calls."""

import json
from datetime import timedelta
from unittest.mock import patch

from django.test import Client, TestCase
from django.utils import timezone

from .gateway import Generation, OfflineGateway
from .service import process_turn


class BrokenGateway:
    def generate(self, **kwargs):
        raise RuntimeError("Provider unavailable")


class BadJSONGateway:
    def generate(self, **kwargs):
        return Generation("{bad", "fake")


class CourseWebTests(TestCase):
    def test_all_four_modules_render(self):
        for stage in range(1, 5):
            response = self.client.get(f"/?stage={stage}")
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, f"MODULE 0{stage}")

    def test_csrf_blocks_unsafe_post(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post("/chat/1/", {"message": "Hello"}).status_code, 403)

    def test_module_1_does_not_store_history_or_invent_policy(self):
        self.client.post("/chat/1/", {"message": "What is your warranty?"})
        page = self.client.get("/?stage=1")
        self.assertContains(page, "do not have approved information")
        self.assertNotIn("m2_history", self.client.session)

    def test_module_2_uses_bounded_context_and_failure_is_atomic(self):
        self.client.post("/chat/2/", {"message": "My order is A123"})
        self.client.post("/chat/2/", {"message": "What is my order number?"})
        page = self.client.get("/?stage=2")
        self.assertContains(page, "You reported order A123 earlier")
        self.assertEqual(len(self.client.session["m2_history"]), 4)
        with patch("support.views.get_gateway", return_value=BrokenGateway()):
            self.client.post("/chat/2/", {"message": "New question"})
        self.assertEqual(len(self.client.session["m2_history"]), 4)
        for i in range(8):
            self.client.post("/chat/2/", {"message": f"Message {i}"})
        self.assertLessEqual(len(self.client.session["m2_history"]), 8)

    def test_module_3_policy_route_handoff_validation_and_evaluation(self):
        self.client.post("/chat/3/", {"message": "What is the return policy?"})
        page = self.client.get("/?stage=3")
        self.assertContains(page, "answer_from_approved_info")
        self.assertContains(page, "30 days")
        self.client.post("/chat/3/", {"message": "Cancel my order"})
        page = self.client.get("/?stage=3")
        self.assertContains(page, "No action has been completed")
        self.assertEqual(len(self.client.session["m3_history"]), 4)
        with patch("support.views.get_gateway", return_value=BadJSONGateway()):
            self.client.post("/chat/3/", {"message": "Return policy?"})
        self.assertContains(self.client.get("/?stage=3"), "cannot process that safely")
        self.assertEqual(len(self.client.session["m3_history"]), 4)
        self.client.post("/evaluation/")
        page = self.client.get("/?stage=3")
        self.assertContains(page, "OFFLINE REGRESSION")
        self.assertContains(page, "24 expected routes")

    def test_module_3_keeps_short_context_for_clarification(self):
        self.client.post("/chat/3/", {"message": "Where is my order?"})
        self.assertEqual(self.client.session["m3_history"][-1]["content"], "What is the order number?")
        self.client.post("/chat/3/", {"message": "A123"})
        self.assertEqual(len(self.client.session["m3_history"]), 4)
        self.assertEqual(self.client.session["last_result"]["route"], "handoff")

    def test_module_4_asks_resumes_corrects_and_drops_raw_history(self):
        self.client.post("/chat/2/", {"message": "Earlier private message"})
        self.client.post("/chat/3/", {"message": "Earlier route message"})
        self.client.post("/chat/4/", {"message": "Where is my order?"})
        self.assertNotIn("m2_history", self.client.session)
        self.assertNotIn("m3_history", self.client.session)
        self.assertEqual(self.client.session["m4_state"]["pending_question"], "What is the order number?")
        self.client.post("/chat/4/", {"message": "A123"})
        self.assertEqual(self.client.session["m4_state"]["current_facts"]["order_reference"]["value"], "A123")
        self.client.post("/chat/4/", {"message": "Actually order B456"})
        state = self.client.session["m4_state"]
        self.assertEqual(state["current_facts"]["order_reference"]["value"], "B456")
        self.assertEqual(state["superseded_facts"][-1]["value"], "A123")
        self.client.post("/state/correct/", {"key": "order_reference", "value": "C789"})
        self.assertEqual(self.client.session["m4_state"]["current_facts"]["order_reference"]["value"], "C789")

    def test_module_4_browser_isolation_expiry_and_deletion(self):
        first = Client()
        second = Client()
        first.post("/chat/4/", {"message": "Order A123"})
        self.assertNotIn("order_reference", second.get("/?stage=4").context["state"]["current_facts"])
        first.post("/state/retention/", {"choice": "until_expiry"})
        self.assertEqual(first.session["m4_state"]["retention_choice"], "until_expiry")
        self.assertFalse(first.session.get_expire_at_browser_close())
        state = first.session["m4_state"]
        state["expires_at"] = (timezone.now() - timedelta(seconds=1)).isoformat()
        session = first.session
        session["m4_state"] = state
        session.save()
        page = first.get("/?stage=4")
        self.assertNotIn("order_reference", page.context["state"]["current_facts"])
        first.post("/chat/4/", {"message": "Order D111"})
        first.post("/state/delete/")
        self.assertNotIn("m4_state", first.session)
        self.assertNotIn("order_reference", first.get("/?stage=4").context["state"]["current_facts"])

    def test_module_4_invalid_model_result_leaves_state_unchanged(self):
        self.client.post("/chat/4/", {"message": "Order A123"})
        old = self.client.session["m4_state"]["current_facts"].copy()
        with patch("support.views.get_gateway", return_value=BadJSONGateway()):
            self.client.post("/chat/4/", {"message": "Actually order B456"})
        self.assertEqual(self.client.session["m4_state"]["current_facts"], old)

    def test_module_4_health_report_stays_reported_and_handoffs(self):
        self.client.post("/chat/4/", {"message": "I have a headache. What dose?"})
        page = self.client.get("/?stage=4")
        self.assertContains(page, "support professional")
        self.assertEqual(self.client.session["m4_state"]["current_facts"]["reported_symptom"]["source"], "reported_by_customer")

    def test_agent_is_the_default_page(self):
        self.assertContains(self.client.get("/"), "MODULES 01–04")

    def test_agent_routes_remembers_facts_and_answers_with_context(self):
        self.client.post("/chat/5/", {"message": "Where is my order?"})
        self.assertEqual(self.client.session["last_result"]["route"], "ask_clarifying_question")
        self.client.post("/chat/5/", {"message": "A123"})
        self.assertEqual(self.client.session["m4_state"]["current_facts"]["order_reference"]["value"], "A123")
        self.assertIn("No action has been completed", self.client.session["last_result"]["response"])

        calls = []
        real = OfflineGateway()

        class Recording:
            def generate(self, **kwargs):
                calls.append(kwargs)
                return real.generate(**kwargs)

        with patch("support.views.get_gateway", return_value=Recording()):
            self.client.post("/chat/5/", {"message": "What is the return policy?"})
        page = self.client.get("/?stage=5")
        self.assertContains(page, "30 days")
        self.assertContains(page, "answer_from_approved_info")
        self.assertEqual([c["stage"] for c in calls], [4, 5])
        history, latest = calls[1]["messages"][:-1], json.loads(calls[1]["messages"][-1]["content"])
        self.assertEqual(history[0], {"role": "user", "content": "Where is my order?"})
        self.assertEqual(latest["reported_facts"], {"order_reference": "A123"})
        self.assertEqual(len(self.client.session["agent_history"]), 6)

        self.client.post("/state/correct/", {"key": "order_reference", "value": "B456", "stage": "5"})
        self.assertEqual(self.client.session["m4_state"]["current_facts"]["order_reference"]["value"], "B456")
        response = self.client.post("/state/delete/", {"stage": "5"})
        self.assertEqual(response["Location"], "/?stage=5")
        self.assertNotIn("agent_history", self.client.session)
        self.assertNotIn("m4_state", self.client.session)

    def test_agent_failed_turn_is_not_committed(self):
        self.client.post("/chat/5/", {"message": "Where is my order?"})
        with patch("support.views.get_gateway", return_value=BadJSONGateway()):
            self.client.post("/chat/5/", {"message": "A123"})
        self.assertEqual(self.client.session["last_result"]["status"], "error")
        self.assertEqual(len(self.client.session["agent_history"]), 2)
        self.assertEqual(self.client.session["m4_state"]["current_facts"], {})
