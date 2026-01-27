from django.db import IntegrityError
from django.test import TestCase

from nbms_app.models import License, Organisation, SourceDocument, User


class CatalogVocabProvenanceTests(TestCase):
    def test_license_unique_code(self):
        License.objects.create(code="CC-BY", title="Creative Commons Attribution")
        with self.assertRaises(IntegrityError):
            License.objects.create(code="CC-BY", title="Duplicate")

    def test_source_document_create(self):
        org = Organisation.objects.create(name="Org A")
        user = User.objects.create_user(username="owner", password="pass1234", organisation=org)
        doc = SourceDocument.objects.create(
            title="COP-15 Decision 15/4",
            source_url="https://www.cbd.int/",
            citation="CBD COP-15",
            created_by=user,
        )
        self.assertEqual(doc.created_by_id, user.id)
