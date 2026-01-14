from django.conf import settings
from django.test.runner import DiscoverRunner


class NBMSTestRunner(DiscoverRunner):
    def build_suite(self, test_labels=None, extra_tests=None, **kwargs):
        if not test_labels:
            test_labels = [str(settings.SRC_DIR)]
        return super().build_suite(test_labels, extra_tests=extra_tests, **kwargs)
