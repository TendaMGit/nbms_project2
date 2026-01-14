from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from nbms_app.models import Organisation, User


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display = ("name", "org_type", "contact_email", "created_at")
    search_fields = ("name", "contact_email")


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Organisation", {"fields": ("organisation",)}),
    )
    list_display = UserAdmin.list_display + ("organisation",)

