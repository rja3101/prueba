# apps/academics/admin.py
from django.contrib import admin

# ────────────────────────────────────────────────────────────────────────────────
# Soporte opcional para import-export
# ────────────────────────────────────────────────────────────────────────────────
try:
    from import_export import resources
    from import_export.admin import ImportExportModelAdmin
except Exception:  # import-export no instalado
    resources = None

    class ImportExportModelAdmin(admin.ModelAdmin):  # fallback
        pass

# ────────────────────────────────────────────────────────────────────────────────
# Import del módulo de modelos completo (para poder preguntar si existen)
# ────────────────────────────────────────────────────────────────────────────────
from . import models as m  # p. ej. m.Course, m.CourseGroup, etc.


# ────────────────────────────────────────────────────────────────────────────────
# Utilidades para registrar de forma segura
# ────────────────────────────────────────────────────────────────────────────────
def model_exists(name: str):
    return getattr(m, name, None)

def safe_list_display(Model, candidates):
    """
    Devuelve solo los nombres que realmente existen como campos o atributos
    en el modelo, para que el admin no reviente por AttributeError.
    """
    safe = []
    # Campos del modelo (FKs incluidos)
    field_names = {f.name for f in Model._meta.get_fields()}
    for n in candidates:
        if n in field_names or hasattr(Model, n):
            safe.append(n)
    return tuple(safe)

def register_safe(model_name: str, admin_cls=None):
    """
    Registra el modelo en el admin si existe.
    Si no se pasa admin_cls, usa ModelAdmin por defecto.
    """
    Model = model_exists(model_name)
    if Model is None:
        return None
    admin.site.register(Model, admin_cls or admin.ModelAdmin)
    return Model


# ────────────────────────────────────────────────────────────────────────────────
# Admin para modelos "core" (Course, CourseGroup, Enrollment, Assessment, Grade)
# ────────────────────────────────────────────────────────────────────────────────

# Course
if model_exists("Course"):
    class CourseAdmin(admin.ModelAdmin):
        # usa solo campos que probablemente existen; se filtran por seguridad
        def get_list_display(self, request):
            Model = m.Course
            candidates = ("code", "name", "credits", "teacher")
            return safe_list_display(Model, candidates)

        def get_search_fields(self, request):
            Model = m.Course
            candidates = ("code", "name", "teacher__username")
            return safe_list_display(Model, candidates)

        def get_list_filter(self, request):
            Model = m.Course
            candidates = ("credits",)
            return safe_list_display(Model, candidates)

    admin.site.register(m.Course, CourseAdmin)

# CourseGroup
if model_exists("CourseGroup"):
    class CourseGroupAdmin(admin.ModelAdmin):
        def get_list_display(self, request):
            Model = m.CourseGroup
            # incluye 'available_slots' si existe como @property en el modelo
            candidates = ("course", "section", "is_lab", "capacity", "enrolled_count", "available_slots")
            return safe_list_display(Model, candidates)

        def get_search_fields(self, request):
            Model = m.CourseGroup
            candidates = ("course__code", "course__name", "section")
            return safe_list_display(Model, candidates)

        def get_list_filter(self, request):
            Model = m.CourseGroup
            candidates = ("is_lab", "course")
            return safe_list_display(Model, candidates)

    admin.site.register(m.CourseGroup, CourseGroupAdmin)

# Enrollment (con import-export si está)
EnrollmentModel = model_exists("Enrollment")
if EnrollmentModel:
    if resources:
        class EnrollmentResource(resources.ModelResource):
            class Meta:
                model = EnrollmentModel
                # ajusta estos campos si tus nombres difieren
                fields = (
                    "student__username",
                    "course_group__course__code",
                    "course_group__section",
                    "created_at",
                )
                export_order = fields  # mismo orden
    else:
        EnrollmentResource = None

    class EnrollmentAdmin(ImportExportModelAdmin):
        if EnrollmentResource:
            resource_class = EnrollmentResource

        def get_list_display(self, request):
            Model = m.Enrollment
            candidates = ("student", "course_group", "created_at")
            return safe_list_display(Model, candidates)

        def get_search_fields(self, request):
            Model = m.Enrollment
            candidates = ("student__username", "course_group__course__code", "course_group__section")
            return safe_list_display(Model, candidates)

        def get_list_filter(self, request):
            Model = m.Enrollment
            candidates = ("course_group__course__code", "created_at")
            return safe_list_display(Model, candidates)

        def get_autocomplete_fields(self, request):
            Model = m.Enrollment
            candidates = ("student", "course_group")
            return safe_list_display(Model, candidates)

    admin.site.register(m.Enrollment, EnrollmentAdmin)

# Assessment
if model_exists("Assessment"):
    class AssessmentAdmin(admin.ModelAdmin):
        def get_list_display(self, request):
            Model = m.Assessment
            # algunos usan title/kind/weight/total_points; otros usan name/weight
            candidates = ("course_group", "title", "name", "kind", "weight", "total_points")
            return safe_list_display(Model, candidates)

        def get_list_filter(self, request):
            Model = m.Assessment
            candidates = ("kind", "course_group__course__code")
            return safe_list_display(Model, candidates)

        def get_search_fields(self, request):
            Model = m.Assessment
            candidates = ("title", "name", "course_group__course__name")
            return safe_list_display(Model, candidates)

        def get_autocomplete_fields(self, request):
            Model = m.Assessment
            candidates = ("course_group",)
            return safe_list_display(Model, candidates)

    admin.site.register(m.Assessment, AssessmentAdmin)

# Grade (con import-export si está) — REEMPLAZO COMPLETO
GradeModel = model_exists("Grade")
if GradeModel:
    if resources:
        from import_export import resources
        from import_export.fields import Field

        class GradeResource(resources.ModelResource):
            # columnas virtuales (no dependen de nombres exactos en los modelos)
            student_username = Field(column_name="student_username")
            assessment_label = Field(column_name="assessment")
            points = Field(column_name="points")

            def dehydrate_student_username(self, obj):
                u = getattr(obj, "student", None)
                return getattr(u, "username", str(u)) if u else ""

            def dehydrate_assessment_label(self, obj):
                a = getattr(obj, "assessment", None)
                if not a:
                    return ""
                # prioriza title > name > str(a)
                return getattr(a, "title", getattr(a, "name", str(a)))

            def dehydrate_points(self, obj):
                # prioriza score > value > ""
                if hasattr(obj, "score"):
                    return obj.score
                if hasattr(obj, "value"):
                    return obj.value
                return ""

            class Meta:
                model = m.Grade
                fields = ("id", "student_username", "assessment_label", "points")
                export_order = ("id", "student_username", "assessment_label", "points")
    else:
        GradeResource = None

    class GradeAdmin(ImportExportModelAdmin):
        if GradeResource:
            resource_class = GradeResource

        def get_list_display(self, request):
            Model = m.Grade
            # mostrará 'score' o 'value' según exista
            candidates = ("student", "assessment", "score", "value")
            return safe_list_display(Model, candidates)

        def get_search_fields(self, request):
            # construimos dinámicamente para evitar FieldError si no existe 'title' o 'name'
            fields = ["student__username"]
            Assess = model_exists("Assessment")
            if Assess:
                assess_field_names = {f.name for f in Assess._meta.get_fields()}
                if "title" in assess_field_names:
                    fields.append("assessment__title")
                if "name" in assess_field_names:
                    fields.append("assessment__name")
            return tuple(fields)

        def get_list_filter(self, request):
            # solo agregamos filtros que existan
            filters = []
            Assess = model_exists("Assessment")
            if Assess:
                assess_field_names = {f.name for f in Assess._meta.get_fields()}
                if "kind" in assess_field_names:
                    filters.append("assessment__kind")
            # si CourseGroup y Course existen, intentamos el code
            try:
                model_exists("CourseGroup")
                model_exists("Course")
                filters.append("assessment__course_group__course__code")
            except Exception:
                pass
            return tuple(filters)

        def get_autocomplete_fields(self, request):
            Model = m.Grade
            candidates = ("student", "assessment")
            return safe_list_display(Model, candidates)

    admin.site.register(m.Grade, GradeAdmin)
# --- FIN REEMPLAZO ---

# ────────────────────────────────────────────────────────────────────────────────
# Admin para currícula, prerrequisitos y emparejamientos (opcionales)
# ────────────────────────────────────────────────────────────────────────────────

if model_exists("Curriculum"):
    class CurriculumAdmin(admin.ModelAdmin):
        def get_list_display(self, request):
            return safe_list_display(m.Curriculum, ("code", "name"))
        def get_search_fields(self, request):
            return safe_list_display(m.Curriculum, ("code", "name"))
    admin.site.register(m.Curriculum, CurriculumAdmin)

if model_exists("CoursePrerequisite"):
    class CoursePrerequisiteAdmin(admin.ModelAdmin):
        def get_list_display(self, request):
            return safe_list_display(m.CoursePrerequisite, ("course", "prerequisite", "min_grade"))
        def get_search_fields(self, request):
            return safe_list_display(m.CoursePrerequisite, ("course__code", "prerequisite__code"))
        def get_autocomplete_fields(self, request):
            return safe_list_display(m.CoursePrerequisite, ("course", "prerequisite"))
    admin.site.register(m.CoursePrerequisite, CoursePrerequisiteAdmin)

if model_exists("CourseCorequisite"):
    class CourseCorequisiteAdmin(admin.ModelAdmin):
        def get_list_display(self, request):
            return safe_list_display(m.CourseCorequisite, ("course", "corequisite"))
        def get_search_fields(self, request):
            return safe_list_display(m.CourseCorequisite, ("course__code", "corequisite__code"))
        def get_autocomplete_fields(self, request):
            return safe_list_display(m.CourseCorequisite, ("course", "corequisite"))
    admin.site.register(m.CourseCorequisite, CourseCorequisiteAdmin)

if model_exists("GroupPairing"):
    class GroupPairingAdmin(admin.ModelAdmin):
        def get_list_display(self, request):
            return safe_list_display(m.GroupPairing, ("theory", "lab"))
        def get_search_fields(self, request):
            return safe_list_display(m.GroupPairing, ("theory__course__code", "lab__course__code"))
        def get_autocomplete_fields(self, request):
            return safe_list_display(m.GroupPairing, ("theory", "lab"))
    admin.site.register(m.GroupPairing, GroupPairingAdmin)

if model_exists("Cohort"):
    class CohortAdmin(admin.ModelAdmin):
        def get_list_display(self, request):
            return safe_list_display(m.Cohort, ("code", "description"))
        def get_search_fields(self, request):
            return safe_list_display(m.Cohort, ("code", "description"))
    admin.site.register(m.Cohort, CohortAdmin)

if model_exists("StudentProfile"):
    class StudentProfileAdmin(admin.ModelAdmin):
        def get_list_display(self, request):
            return safe_list_display(
                m.StudentProfile,
                ("user", "cohort", "curriculum", "approved_credits", "gpa", "has_debt_hold", "has_document_hold"),
            )
        def get_search_fields(self, request):
            return safe_list_display(m.StudentProfile, ("user__username", "cohort__code", "curriculum__code"))
        def get_list_filter(self, request):
            return safe_list_display(m.StudentProfile, ("has_debt_hold", "has_document_hold"))
        def get_autocomplete_fields(self, request):
            return safe_list_display(m.StudentProfile, ("user", "cohort", "curriculum"))
    admin.site.register(m.StudentProfile, StudentProfileAdmin)

# ────────────────────────────────────────────────────────────────────────────────
# Admin para términos/ventanas/reglas (opcionales)
# ────────────────────────────────────────────────────────────────────────────────

if model_exists("Term"):
    class TermAdmin(admin.ModelAdmin):
        def get_list_display(self, request):
            return safe_list_display(m.Term, ("name", "start_date", "end_date"))
        def get_search_fields(self, request):
            return safe_list_display(m.Term, ("name",))
        date_hierarchy = "start_date" if hasattr(m.Term, "start_date") else None
    admin.site.register(m.Term, TermAdmin)

if model_exists("EnrollmentWindow"):
    class EnrollmentWindowAdmin(admin.ModelAdmin):
        def get_list_display(self, request):
            # 'is_open_now' como método dinámico en el admin
            base = safe_list_display(m.EnrollmentWindow, ("term", "open_at", "close_at"))
            return base + ("is_open_now",)
        def get_autocomplete_fields(self, request):
            return safe_list_display(m.EnrollmentWindow, ("term",))
        date_hierarchy = "open_at" if hasattr(m.EnrollmentWindow, "open_at") else None

        @admin.display(description="Abierto ahora")
        def is_open_now(self, obj):
            try:
                from django.utils import timezone
                now = timezone.now()
                return getattr(obj, "open_at") <= now <= getattr(obj, "close_at")
            except Exception:
                return False

    admin.site.register(m.EnrollmentWindow, EnrollmentWindowAdmin)

if model_exists("TermRule"):
    class TermRuleAdmin(admin.ModelAdmin):
        def get_list_display(self, request):
            return safe_list_display(
                m.TermRule,
                ("term", "min_credits", "max_credits", "gpa_threshold", "max_credits_low_gpa", "cart_hold_minutes"),
            )
        def get_autocomplete_fields(self, request):
            return safe_list_display(m.TermRule, ("term",))
    admin.site.register(m.TermRule, TermRuleAdmin)

# ────────────────────────────────────────────────────────────────────────────────
# Admin para carrito y auditoría (opcionales)
# ────────────────────────────────────────────────────────────────────────────────

if model_exists("EnrollmentCart"):
    class EnrollmentCartAdmin(admin.ModelAdmin):
        def get_list_display(self, request):
            return safe_list_display(m.EnrollmentCart, ("student", "term", "is_active", "confirmed_at", "created_at"))
        def get_list_filter(self, request):
            return safe_list_display(m.EnrollmentCart, ("is_active", "term"))
        def get_search_fields(self, request):
            return safe_list_display(m.EnrollmentCart, ("student__username",))
        date_hierarchy = "created_at" if hasattr(m.EnrollmentCart, "created_at") else None
        def get_autocomplete_fields(self, request):
            return safe_list_display(m.EnrollmentCart, ("student", "term"))
    admin.site.register(m.EnrollmentCart, EnrollmentCartAdmin)

if model_exists("CartItem"):
    class CartItemAdmin(admin.ModelAdmin):
        def get_list_display(self, request):
            return safe_list_display(m.CartItem, ("cart", "course_group", "reserved_until", "created_at"))
        def get_search_fields(self, request):
            return safe_list_display(m.CartItem, ("cart__student__username", "course_group__course__code", "course_group__section"))
        def get_list_filter(self, request):
            return safe_list_display(m.CartItem, ("course_group__course__code",))
        def get_autocomplete_fields(self, request):
            return safe_list_display(m.CartItem, ("cart", "course_group"))
    admin.site.register(m.CartItem, CartItemAdmin)

if model_exists("CapReservation"):
    class CapReservationAdmin(admin.ModelAdmin):
        def get_list_display(self, request):
            return safe_list_display(m.CapReservation, ("course_group", "student", "term", "reserved_until", "created_at"))
        def get_search_fields(self, request):
            return safe_list_display(m.CapReservation, ("student__username", "course_group__course__code", "course_group__section"))
        def get_list_filter(self, request):
            return safe_list_display(m.CapReservation, ("term", "course_group__course__code"))
        def get_autocomplete_fields(self, request):
            return safe_list_display(m.CapReservation, ("course_group", "student", "term"))
    admin.site.register(m.CapReservation, CapReservationAdmin)

if model_exists("PaymentOrder"):
    class PaymentOrderAdmin(admin.ModelAdmin):
        def get_list_display(self, request):
            return safe_list_display(m.PaymentOrder, ("student", "term", "amount", "status", "created_at"))
        def get_list_filter(self, request):
            return safe_list_display(m.PaymentOrder, ("status", "term"))
        def get_search_fields(self, request):
            return safe_list_display(m.PaymentOrder, ("student__username",))
        date_hierarchy = "created_at" if hasattr(m.PaymentOrder, "created_at") else None
        def get_autocomplete_fields(self, request):
            return safe_list_display(m.PaymentOrder, ("student", "term"))
    admin.site.register(m.PaymentOrder, PaymentOrderAdmin)

if model_exists("EnrollmentAttempt"):
    class EnrollmentAttemptAdmin(admin.ModelAdmin):
        def get_list_display(self, request):
            return safe_list_display(m.EnrollmentAttempt, ("student", "term", "action", "created_at"))
        def get_search_fields(self, request):
            return safe_list_display(m.EnrollmentAttempt, ("student__username", "action"))
        def get_list_filter(self, request):
            return safe_list_display(m.EnrollmentAttempt, ("action", "term"))
        date_hierarchy = "created_at" if hasattr(m.EnrollmentAttempt, "created_at") else None
        def get_readonly_fields(self, request, obj=None):
            return safe_list_display(m.EnrollmentAttempt, ("payload", "result"))
        def get_autocomplete_fields(self, request):
            return safe_list_display(m.EnrollmentAttempt, ("student", "term"))
    admin.site.register(m.EnrollmentAttempt, EnrollmentAttemptAdmin)
