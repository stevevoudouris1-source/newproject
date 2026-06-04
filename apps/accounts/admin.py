from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Permission, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = (
        "username",
        "email",
        "role",
        "is_claude_service",
        "is_staff",
        "is_active",
    )
    list_filter = ("role", "is_claude_service", "is_staff", "is_active")
    fieldsets = DjangoUserAdmin.fieldsets + (("Turn 5", {"fields": ("role", "is_claude_service")}),)
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("Turn 5", {"fields": ("role", "is_claude_service")}),
    )


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("user", "name", "resource_type", "resource_id")
    list_filter = ("name", "resource_type")
    search_fields = ("user__username", "user__email", "name")
    autocomplete_fields = ("user",)
