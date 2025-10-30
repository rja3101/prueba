from django.contrib import admin
from .models import User, Role

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "username", "email", "first_name", "last_name", "role", "is_staff", "is_active")
    list_filter = ("is_staff", "is_active", "role")
    search_fields = ("username", "email", "first_name", "last_name")
