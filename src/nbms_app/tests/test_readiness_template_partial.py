from django.template.loader import render_to_string
from django.test import TestCase


class ReadinessCardTemplateTests(TestCase):
    def test_readiness_card_partial_renders(self):
        card = {
            "title": "Readiness",
            "band": "green",
            "band_label": "Green",
            "score": 88,
            "score_breakdown": [{"label": "Sections", "score": 90, "weight": 30}],
            "checks": [{"label": "Sections", "state": "ok", "count": 5}],
        }
        html = render_to_string("nbms_app/includes/readiness_card.html", {"card": card})
        self.assertIn("Readiness", html)
