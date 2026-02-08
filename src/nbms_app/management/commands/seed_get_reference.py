from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from nbms_app.models import IucnGetNode
from nbms_app.services.registry_catalog import GET_REFERENCE_ROWS


class Command(BaseCommand):
    help = "Seed IUCN Global Ecosystem Typology (GET) reference nodes for crosswalk workflows."

    @transaction.atomic
    def handle(self, *args, **options):
        nodes_by_code = {}
        for row in GET_REFERENCE_ROWS:
            node, _ = IucnGetNode.objects.update_or_create(
                code=row["code"],
                defaults={
                    "level": row["level"],
                    "label": row["label"],
                    "description": row.get("description", ""),
                    "is_active": True,
                },
            )
            nodes_by_code[row["code"]] = node

        for row in GET_REFERENCE_ROWS:
            parent_code = (row.get("parent") or "").strip()
            if not parent_code:
                continue
            node = nodes_by_code[row["code"]]
            parent = nodes_by_code.get(parent_code)
            if node.parent_id != (parent.id if parent else None):
                node.parent = parent
                node.save(update_fields=["parent", "updated_at"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded GET reference dictionary. Total active nodes={IucnGetNode.objects.filter(is_active=True).count()}."
            )
        )
