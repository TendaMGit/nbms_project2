from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("nbms_app", "0022_sensitivityclass_frameworkindicator_framework_target_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="reportingsnapshot",
            name="readiness_report_json",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="reportingsnapshot",
            name="readiness_overall_ready",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="reportingsnapshot",
            name="readiness_blocking_gap_count",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
