from django.contrib import admin
from .models import Schedule, Session, Attendance

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ("id", "course_group", "day", "start_time", "end_time", "classroom")
    list_filter = ("day", "classroom", "course_group__course")  # antes era 'course'
    search_fields = ("course_group__course__code", "course_group__course__name", "course_group__section", "classroom")

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("id", "schedule", "date", "created_at")
    list_filter = ("date", "schedule__course_group__course")  # antes era schedule__course
    search_fields = ("schedule__course_group__course__name", "schedule__course_group__section")

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "session", "entry_time", "ip_address")
    list_filter = ("session__date", "student")
    search_fields = ("student__username", "ip_address")
