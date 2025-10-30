from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from .models import (
    # básicos existentes
    Course, CourseGroup, Enrollment, Assessment, Grade,
    # académicos extra
    Term, EnrollmentWindow, TermRule,
    Curriculum, CoursePrerequisite, CourseCorequisite, GroupPairing,
    Cohort, StudentProfile,
    # matrícula SISCAD
    EnrollmentCart, CartItem, CapReservation, PaymentOrder, EnrollmentAttempt,
)

# =========================
# Recursos import/export
# =========================

class EnrollmentResource(resources.ModelResource):
    class Meta:
        model = Enrollment
        fields = (
            "student__username",
            "course_group__course__code",
            "course_group__section",
            "created_at",
        )
        export_order = fields

class GradeResource(resources.ModelResource):
    class Meta:
        model = Grade
        fields = (
            "student__username",
            "assessment__course_group__course__code",
            "assessment__title",
            "score",
        )
        export_order = fields

# =========================
# Admin básicos
# =========================

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "credits", "teacher")
    search_fields = ("code", "name", "teacher__username")
    list_filter = ("credits",)

@admin.register(CourseGroup)
class CourseGroupAdmin(admin.ModelAdmin):
    list_display = ("course", "section", "is_lab", "capacity", "enrolled_count", "available_now")
    list_filter = ("is_lab", "course")
    search_fields = ("course__code", "course__name", "section")

    @admin.display(description="Disp. ahora")
    def available_now(self, obj):
        # requiere la @property available_slots en el modelo
        try:
            return obj.available_slots
        except Exception:
            # fallback si no existe la propiedad
            return "-"

@admin.register(Enrollment)
class EnrollmentAdmin(ImportExportModelAdmin):
    resource_class = EnrollmentResource
    list_display = ("student", "course_group", "created_at")
    search_fields = ("student__username", "course_group__course__code", "course_group__section")
    list_filter = ("course_group__course__code", "created_at")
    autocomplete_fields = ("student", "course_group")

@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ("course_group", "title", "kind", "weight", "total_points")
    list_filter = ("kind", "course_group__course__code")
    search_fields = ("title", "course_group__course__name")
    autocomplete_fields = ("course_group",)

@admin.register(Grade)
class GradeAdmin(ImportExportModelAdmin):
    resource_class = GradeResource
    list_display = ("student", "assessment", "score")
    search_fields = ("student__username", "assessment__title")
    list_filter = ("assessment__course_group__course__code", "assessment__kind")
    autocomplete_fields = ("student", "assessment")

# =========================
# Currícula, prerrequisitos y emparejamientos
# =========================

@admin.register(Curriculum)
class CurriculumAdmin(admin.ModelAdmin):
    list_display = ("code", "name")
    search_fields = ("code", "name")

@admin.register(CoursePrerequisite)
class CoursePrerequisiteAdmin(admin.ModelAdmin):
    list_display = ("course", "prerequisite", "min_grade")
    search_fields = ("course__code", "prerequisite__code")
    autocomplete_fields = ("course", "prerequisite")

@admin.register(CourseCorequisite)
class CourseCorequisiteAdmin(admin.ModelAdmin):
    list_display = ("course", "corequisite")
    search_fields = ("course__code", "corequisite__code")
    autocomplete_fields = ("course", "corequisite")

@admin.register(GroupPairing)
class GroupPairingAdmin(admin.ModelAdmin):
    list_display = ("theory", "lab")
    search_fields = ("theory__course__code", "lab__course__code")
    autocomplete_fields = ("theory", "lab")

@admin.register(Cohort)
class CohortAdmin(admin.ModelAdmin):
    list_display = ("code", "description")
    search_fields = ("code", "description")

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "cohort", "curriculum", "approved_credits", "gpa", "has_debt_hold", "has_document_hold")
    search_fields = ("user__username", "cohort__code", "curriculum__code")
    list_filter = ("has_debt_hold", "has_document_hold")
    autocomplete_fields = ("user", "cohort", "curriculum")

# =========================
# Término, ventana y reglas
# =========================

@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date")
    search_fields = ("name",)
    date_hierarchy = "start_date"

@admin.register(EnrollmentWindow)
class EnrollmentWindowAdmin(admin.ModelAdmin):
    list_display = ("term", "open_at", "close_at", "is_open_now")
    date_hierarchy = "open_at"
    autocomplete_fields = ("term",)

    @admin.display(description="Abierto ahora")
    def is_open_now(self, obj):
        from django.utils import timezone
        now = timezone.now()
        return obj.open_at <= now <= obj.close_at

@admin.register(TermRule)
class TermRuleAdmin(admin.ModelAdmin):
    list_display = ("term", "min_credits", "max_credits", "gpa_threshold", "max_credits_low_gpa", "cart_hold_minutes")
    autocomplete_fields = ("term",)

# =========================
# Carrito SISCAD y auditoría
# =========================

@admin.register(EnrollmentCart)
class EnrollmentCartAdmin(admin.ModelAdmin):
    list_display = ("student", "term", "is_active", "confirmed_at", "created_at")
    list_filter = ("is_active", "term")
    search_fields = ("student__username",)
    date_hierarchy = "created_at"
    autocomplete_fields = ("student", "term")

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("cart", "course_group", "reserved_until", "created_at")
    search_fields = ("cart__student__username", "course_group__course__code", "course_group__section")
    list_filter = ("course_group__course__code",)
    autocomplete_fields = ("cart", "course_group")

@admin.register(CapReservation)
class CapReservationAdmin(admin.ModelAdmin):
    list_display = ("course_group", "student", "term", "reserved_until", "created_at")
    search_fields = ("student__username", "course_group__course__code", "course_group__section")
    list_filter = ("term", "course_group__course__code")
    autocomplete_fields = ("course_group", "student", "term")

@admin.register(PaymentOrder)
class PaymentOrderAdmin(admin.ModelAdmin):
    list_display = ("student", "term", "amount", "status", "created_at")
    list_filter = ("status", "term")
    search_fields = ("student__username",)
    date_hierarchy = "created_at"
    autocomplete_fields = ("student", "term")

@admin.register(EnrollmentAttempt)
class EnrollmentAttemptAdmin(admin.ModelAdmin):
    list_display = ("student", "term", "action", "created_at")
    search_fields = ("student__username", "action")
    list_filter = ("action", "term")
    date_hierarchy = "created_at"
    readonly_fields = ("payload", "result")  # para revisar JSON sin editar
    autocomplete_fields = ("student", "term")
