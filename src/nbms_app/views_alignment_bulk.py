from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from nbms_app.forms_alignment_bulk import (
    BulkIndicatorAlignmentForm,
    BulkIndicatorLinkRemoveForm,
    BulkTargetAlignmentForm,
    BulkTargetLinkRemoveForm,
)
from nbms_app.models import ReportingInstance
from nbms_app.services.alignment_bulk import (
    bulk_archive_indicator_links,
    bulk_archive_target_links,
    bulk_link_indicators,
    bulk_link_targets,
    orphan_indicators_for_instance,
    orphan_targets_for_instance,
    visible_framework_indicators_for_user,
    visible_framework_targets_for_user,
    visible_frameworks_for_user,
    visible_indicator_links_for_instance,
    visible_orphan_indicators_queryset,
    visible_orphan_targets_queryset,
    visible_selected_indicators_queryset,
    visible_selected_targets_queryset,
    visible_target_links_for_instance,
)
from nbms_app.views import _require_alignment_manager, _require_section_progress_access, staff_or_system_admin_required


def _safe_bulk_message(request, result):
    created = result.get("created", 0)
    skipped = result.get("skipped", 0)
    failed = result.get("failed", 0)
    if failed:
        messages.warning(
            request,
            "Some items could not be linked due to access restrictions or missing consent.",
        )
    return f"Created: {created}. Skipped: {skipped}. Failed: {failed}."


@staff_or_system_admin_required
def alignment_orphans_targets(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    _require_section_progress_access(instance, request.user)
    _require_alignment_manager(request.user)

    query = request.GET.get("q", "").strip()
    framework_code = request.GET.get("framework", "").strip()
    picker_query = request.GET.get("picker_q", "").strip()

    orphan_items = orphan_targets_for_instance(instance, request.user, query=query)
    orphan_targets_qs = visible_orphan_targets_queryset(instance, request.user, orphan_items)
    selected_targets_qs = visible_selected_targets_queryset(instance, request.user)

    framework_targets_qs = visible_framework_targets_for_user(
        instance=instance,
        user=request.user,
        framework_code=framework_code or None,
        query=picker_query or None,
    )
    targets_queryset = orphan_targets_qs if request.method != "POST" else selected_targets_qs
    form = BulkTargetAlignmentForm(
        request.POST or None,
        targets_queryset=targets_queryset,
        framework_targets_queryset=framework_targets_qs,
    )

    if request.method == "POST":
        _require_alignment_manager(request.user)
        if form.is_valid():
            result = bulk_link_targets(
                instance=instance,
                user=request.user,
                targets=form.cleaned_data["national_targets"],
                framework_targets=form.cleaned_data["framework_targets"],
                relation_type=form.cleaned_data["relation_type"],
                confidence=form.cleaned_data.get("confidence"),
                notes=form.cleaned_data.get("notes") or "",
                source=form.cleaned_data.get("source") or "",
            )
            messages.success(request, _safe_bulk_message(request, result))
            return redirect(
                "nbms_app:alignment_orphans_targets",
                instance_uuid=instance.uuid,
            )

    frameworks = visible_frameworks_for_user(request.user)
    return render(
        request,
        "nbms_app/alignment/orphans_national_targets.html",
        {
            "instance": instance,
            "orphans": orphan_items,
            "form": form,
            "frameworks": frameworks,
            "selected_framework": framework_code,
            "query": query,
            "picker_query": picker_query,
        },
    )


@staff_or_system_admin_required
def alignment_orphans_indicators(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    _require_section_progress_access(instance, request.user)
    _require_alignment_manager(request.user)

    query = request.GET.get("q", "").strip()
    framework_code = request.GET.get("framework", "").strip()
    picker_query = request.GET.get("picker_q", "").strip()

    orphan_items = orphan_indicators_for_instance(instance, request.user, query=query)
    orphan_indicators_qs = visible_orphan_indicators_queryset(instance, request.user, orphan_items)
    selected_indicators_qs = visible_selected_indicators_queryset(instance, request.user)

    framework_indicators_qs = visible_framework_indicators_for_user(
        instance=instance,
        user=request.user,
        framework_code=framework_code or None,
        query=picker_query or None,
    )
    indicators_queryset = orphan_indicators_qs if request.method != "POST" else selected_indicators_qs
    form = BulkIndicatorAlignmentForm(
        request.POST or None,
        indicators_queryset=indicators_queryset,
        framework_indicators_queryset=framework_indicators_qs,
    )

    if request.method == "POST":
        _require_alignment_manager(request.user)
        if form.is_valid():
            result = bulk_link_indicators(
                instance=instance,
                user=request.user,
                indicators=form.cleaned_data["indicators"],
                framework_indicators=form.cleaned_data["framework_indicators"],
                relation_type=form.cleaned_data["relation_type"],
                confidence=form.cleaned_data.get("confidence"),
                notes=form.cleaned_data.get("notes") or "",
                source=form.cleaned_data.get("source") or "",
            )
            messages.success(request, _safe_bulk_message(request, result))
            return redirect(
                "nbms_app:alignment_orphans_indicators",
                instance_uuid=instance.uuid,
            )

    frameworks = visible_frameworks_for_user(request.user)
    return render(
        request,
        "nbms_app/alignment/orphans_indicators.html",
        {
            "instance": instance,
            "orphans": orphan_items,
            "form": form,
            "frameworks": frameworks,
            "selected_framework": framework_code,
            "query": query,
            "picker_query": picker_query,
        },
    )


@staff_or_system_admin_required
def alignment_mappings_manage(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    _require_section_progress_access(instance, request.user)
    _require_alignment_manager(request.user)

    target_links = visible_target_links_for_instance(instance, request.user)
    indicator_links = visible_indicator_links_for_instance(instance, request.user)

    target_form = BulkTargetLinkRemoveForm(request.POST or None, links_queryset=target_links)
    indicator_form = BulkIndicatorLinkRemoveForm(request.POST or None, links_queryset=indicator_links)

    if request.method == "POST":
        _require_alignment_manager(request.user)
        action = request.POST.get("bulk_action")
        if action == "targets" and target_form.is_valid():
            removed = bulk_archive_target_links(user=request.user, links=target_form.cleaned_data["links"])
            messages.success(request, f"Archived {removed} target alignment(s).")
            return redirect("nbms_app:alignment_mappings_manage", instance_uuid=instance.uuid)
        if action == "indicators" and indicator_form.is_valid():
            removed = bulk_archive_indicator_links(user=request.user, links=indicator_form.cleaned_data["links"])
            messages.success(request, f"Archived {removed} indicator alignment(s).")
            return redirect("nbms_app:alignment_mappings_manage", instance_uuid=instance.uuid)

    return render(
        request,
        "nbms_app/alignment/mappings_manage.html",
        {
            "instance": instance,
            "target_links": target_links,
            "indicator_links": indicator_links,
            "target_form": target_form,
            "indicator_form": indicator_form,
        },
    )
