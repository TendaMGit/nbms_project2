from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import reverse

from nbms_app.models import Evidence, LifecycleStatus, Organisation, SensitivityLevel, User


class ApiAbacTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.org = Organisation.objects.create(name="Org A")
        self.user = User.objects.create_user(username="owner", password="pass1234", organisation=self.org)
        self.evidence_public = Evidence.objects.create(
            title="Public Evidence",
            organisation=self.org,
            created_by=self.user,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.PUBLIC,
        )
        self.evidence_internal = Evidence.objects.create(
            title="Internal Evidence",
            organisation=self.org,
            created_by=self.user,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.INTERNAL,
        )

    def test_api_list_filters_restricted(self):
        url = reverse("evidence-list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        titles = {item["title"] for item in resp.data["results"]}
        self.assertIn(self.evidence_public.title, titles)
        self.assertNotIn(self.evidence_internal.title, titles)

    def test_api_detail_blocks_internal_for_anonymous(self):
        url = reverse("evidence-detail", args=[self.evidence_internal.uuid])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)
