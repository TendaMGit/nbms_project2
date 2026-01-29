from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from nbms_app.models import (
    AccessLevel,
    DatasetCatalog,
    Methodology,
    MonitoringProgramme,
    NationalTarget,
    Indicator,
    Organisation,
    SensitivityClass,
    User,
)
from nbms_app.services.authorization import ROLE_CONTRIBUTOR


class CatalogDatasetUiTests(TestCase):
    def setUp(self):
        self.org_a = Organisation.objects.create(name="Org A")
        self.org_b = Organisation.objects.create(name="Org B")
        self.user = User.objects.create_user(
            username="contrib",
            password="pass1234",
            organisation=self.org_a,
        )
        self.user.groups.add(Group.objects.create(name=ROLE_CONTRIBUTOR))

        self.target = NationalTarget.objects.create(
            code="NT-1",
            title="Target 1",
            organisation=self.org_a,
        )
        self.indicator = Indicator.objects.create(
            code="IND-1",
            title="Indicator 1",
            national_target=self.target,
            organisation=self.org_a,
            status="published",
            sensitivity="public",
        )
        self.public_class = SensitivityClass.objects.create(
            sensitivity_code="PUB",
            sensitivity_name="Public",
            access_level_default=AccessLevel.PUBLIC,
        )
        self.programme = MonitoringProgramme.objects.create(
            programme_code="PROG-1",
            title="Programme 1",
            lead_org=self.org_a,
            sensitivity_class=self.public_class,
        )
        self.methodology = Methodology.objects.create(
            methodology_code="METH-1",
            title="Methodology 1",
            owner_org=self.org_a,
        )

    def test_dataset_create_form_renders_catalog_fields(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("nbms_app:dataset_create"))
        self.assertEqual(resp.status_code, 200)
        form = resp.context["form"]
        for field in [
            "dataset_code",
            "title",
            "access_level",
            "custodian_org",
            "sensitivity_class",
            "agreement",
            "programmes",
            "indicators",
            "methodologies",
        ]:
            self.assertIn(field, form.fields)

    def test_dataset_create_post_creates_links(self):
        self.client.force_login(self.user)
        resp = self.client.post(
            reverse("nbms_app:dataset_create"),
            {
                "dataset_code": "DS-1",
                "title": "Dataset 1",
                "access_level": AccessLevel.PUBLIC,
                "custodian_org": str(self.org_a.id),
                "programmes": [str(self.programme.id)],
                "indicators": [str(self.indicator.id)],
                "methodologies": [str(self.methodology.id)],
            },
        )
        self.assertEqual(resp.status_code, 302)
        dataset = DatasetCatalog.objects.get(dataset_code="DS-1")
        self.assertEqual(dataset.programme_links.count(), 1)
        self.assertEqual(dataset.indicator_links.count(), 1)
        self.assertEqual(dataset.methodology_links.count(), 1)

    def test_dataset_create_abac_dropdowns(self):
        restricted_class = SensitivityClass.objects.create(
            sensitivity_code="RES",
            sensitivity_name="Restricted",
            access_level_default=AccessLevel.RESTRICTED,
        )
        programme_b = MonitoringProgramme.objects.create(
            programme_code="PROG-B",
            title="Programme B",
            lead_org=self.org_b,
            sensitivity_class=restricted_class,
        )
        methodology_b = Methodology.objects.create(
            methodology_code="METH-B",
            title="Methodology B",
            owner_org=self.org_b,
        )
        target_b = NationalTarget.objects.create(
            code="NT-B",
            title="Target B",
            organisation=self.org_b,
        )
        indicator_b = Indicator.objects.create(
            code="IND-B",
            title="Indicator B",
            national_target=target_b,
            organisation=self.org_b,
            status="published",
            sensitivity="internal",
        )
        self.client.force_login(self.user)
        resp = self.client.get(reverse("nbms_app:dataset_create"))
        form = resp.context["form"]
        self.assertNotIn(programme_b, list(form.fields["programmes"].queryset))
        self.assertNotIn(methodology_b, list(form.fields["methodologies"].queryset))
        self.assertNotIn(indicator_b, list(form.fields["indicators"].queryset))
