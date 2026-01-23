from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("nbms_app", "0023_reporting_snapshot_readiness"),
    ]

    operations = [
        migrations.CreateModel(
            name="DatasetCatalogIndicatorLink",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("relationship_type", models.CharField(blank=True, choices=[("lead", "Lead"), ("partner", "Partner"), ("supporting", "Supporting"), ("contextual", "Contextual"), ("derived", "Derived")], max_length=20)),
                ("role", models.CharField(blank=True, max_length=100)),
                ("notes", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("source_system", models.CharField(blank=True, max_length=100)),
                ("source_ref", models.CharField(blank=True, max_length=255)),
                ("dataset", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="indicator_links", to="nbms_app.datasetcatalog")),
                ("indicator", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="dataset_catalog_links", to="nbms_app.indicator")),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("dataset", "indicator"), name="uq_dataset_catalog_indicator")
                ],
            },
        ),
    ]
