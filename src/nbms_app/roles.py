from django.contrib.auth.models import Group

CANONICAL_GROUPS = [
    "SystemAdmin",
    "Admin",
    "Secretariat",
    "Data Steward",
    "Indicator Lead",
    "Contributor",
    "Viewer",
    "Security Officer",
    "Community Representative",
]


def get_canonical_groups_queryset():
    return Group.objects.filter(name__in=CANONICAL_GROUPS).order_by("name")
