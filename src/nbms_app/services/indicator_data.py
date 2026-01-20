from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from nbms_app.models import (
    BinaryIndicatorQuestion,
    BinaryIndicatorResponse,
    ConsentRecord,
    ConsentStatus,
    DatasetRelease,
    FrameworkIndicator,
    Indicator,
    IndicatorDataPoint,
    IndicatorDataSeries,
    SensitivityLevel,
)
from nbms_app.services.authorization import filter_queryset_for_user


def _apply_consent_filter(queryset, instance):
    if not instance:
        return queryset
    model = queryset.model
    if not hasattr(model, "sensitivity"):
        return queryset

    content_type = ContentType.objects.get_for_model(model)
    allowed_uuids = ConsentRecord.objects.filter(
        content_type=content_type,
        status=ConsentStatus.GRANTED,
    ).filter(Q(reporting_instance=instance) | Q(reporting_instance__isnull=True)).values_list("object_uuid", flat=True)

    return queryset.filter(
        Q(sensitivity=SensitivityLevel.IPLC_SENSITIVE, uuid__in=allowed_uuids)
        | ~Q(sensitivity=SensitivityLevel.IPLC_SENSITIVE)
    )


def filter_indicator_data_series_for_user(queryset, user, instance=None):
    base_qs = filter_queryset_for_user(queryset, user)
    indicator_ids = filter_queryset_for_user(Indicator.objects.all(), user).values_list("id", flat=True)
    framework_indicator_ids = filter_queryset_for_user(FrameworkIndicator.objects.all(), user).values_list("id", flat=True)
    base_qs = base_qs.filter(Q(indicator_id__in=indicator_ids) | Q(framework_indicator_id__in=framework_indicator_ids))
    return _apply_consent_filter(base_qs, instance)


def filter_indicator_data_points_for_user(queryset, user, instance=None):
    series_ids = filter_indicator_data_series_for_user(
        IndicatorDataSeries.objects.all(), user, instance
    ).values_list("id", flat=True)
    dataset_release_ids = filter_queryset_for_user(DatasetRelease.objects.all(), user).values_list("id", flat=True)
    return queryset.filter(series_id__in=series_ids).filter(
        Q(dataset_release_id__isnull=True) | Q(dataset_release_id__in=dataset_release_ids)
    )


def filter_binary_indicator_questions_for_user(queryset, user, instance=None):
    indicator_qs = filter_queryset_for_user(FrameworkIndicator.objects.all(), user)
    indicator_qs = _apply_consent_filter(indicator_qs, instance)
    indicator_ids = indicator_qs.values_list("id", flat=True)
    return queryset.filter(framework_indicator_id__in=indicator_ids)


def filter_binary_indicator_responses_for_user(queryset, user, instance=None):
    question_ids = filter_binary_indicator_questions_for_user(
        BinaryIndicatorQuestion.objects.all(), user, instance
    ).values_list("id", flat=True)
    qs = queryset.filter(question_id__in=question_ids)
    if instance:
        qs = qs.filter(reporting_instance=instance)
    return qs


def indicator_data_series_for_user(user, instance=None):
    return filter_indicator_data_series_for_user(IndicatorDataSeries.objects.all(), user, instance)


def indicator_data_points_for_user(user, instance=None):
    return filter_indicator_data_points_for_user(IndicatorDataPoint.objects.all(), user, instance)


def binary_indicator_questions_for_user(user, instance=None):
    return filter_binary_indicator_questions_for_user(BinaryIndicatorQuestion.objects.all(), user, instance)


def binary_indicator_responses_for_user(user, instance=None):
    return filter_binary_indicator_responses_for_user(BinaryIndicatorResponse.objects.all(), user, instance)
