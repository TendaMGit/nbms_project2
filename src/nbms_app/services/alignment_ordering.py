def sort_model_items(items):
    return sorted(items, key=lambda obj: (obj.code or "", obj.title or "", str(obj.uuid)))


def sort_dicts(items, *keys):
    def sort_key(item):
        return tuple(item.get(key) or "" for key in keys)

    return sorted(items, key=sort_key)


def sort_framework_link_dicts(items):
    return sort_dicts(items, "framework_code", "code", "title", "uuid")


def order_queryset_by_code_title_uuid(queryset):
    return queryset.order_by("code", "title", "uuid")


def order_queryset_by_framework_code_title_uuid(queryset):
    return queryset.order_by("framework__code", "code", "title", "uuid")


def order_target_links_queryset(queryset):
    return queryset.order_by(
        "national_target__code",
        "framework_target__framework__code",
        "framework_target__code",
        "framework_target__uuid",
    )


def order_indicator_links_queryset(queryset):
    return queryset.order_by(
        "indicator__code",
        "framework_indicator__framework__code",
        "framework_indicator__code",
        "framework_indicator__uuid",
    )
