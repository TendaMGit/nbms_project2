from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from nbms_app.forms import EvidenceForm
from nbms_app.models import SensitivityLevel


class EvidenceUploadValidationTests(TestCase):
    @override_settings(EVIDENCE_MAX_FILE_SIZE=1024, EVIDENCE_ALLOWED_EXTENSIONS=[".pdf"])
    def test_allows_valid_file(self):
        uploaded = SimpleUploadedFile("evidence.pdf", b"valid", content_type="application/pdf")
        form = EvidenceForm(
            data={"title": "Evidence", "sensitivity": SensitivityLevel.INTERNAL},
            files={"file": uploaded},
        )
        self.assertTrue(form.is_valid())

    @override_settings(EVIDENCE_MAX_FILE_SIZE=1024, EVIDENCE_ALLOWED_EXTENSIONS=[".pdf"])
    def test_rejects_disallowed_extension(self):
        uploaded = SimpleUploadedFile("evidence.exe", b"bad", content_type="application/octet-stream")
        form = EvidenceForm(
            data={"title": "Evidence", "sensitivity": SensitivityLevel.INTERNAL},
            files={"file": uploaded},
        )
        self.assertFalse(form.is_valid())
        self.assertIn("file", form.errors)

    @override_settings(EVIDENCE_MAX_FILE_SIZE=4, EVIDENCE_ALLOWED_EXTENSIONS=[".pdf"])
    def test_rejects_oversize_file(self):
        uploaded = SimpleUploadedFile("evidence.pdf", b"too-big", content_type="application/pdf")
        form = EvidenceForm(
            data={"title": "Evidence", "sensitivity": SensitivityLevel.INTERNAL},
            files={"file": uploaded},
        )
        self.assertFalse(form.is_valid())
        self.assertIn("file", form.errors)
