from django.db import models
from django.conf import settings

# --- Cursos y secciones/grupos ---
class Course(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=120)
    credits = models.PositiveSmallIntegerField(default=3)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="courses",
        limit_choices_to={"role__name": "Docente"},
    )

    class Meta:
        verbose_name = "Curso"
        verbose_name_plural = "Cursos"

    def __str__(self):
        return f"{self.code} - {self.name}"

class CourseGroup(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="groups")
    section = models.CharField(max_length=10)  # p.ej. A, B, LAB1
    is_lab = models.BooleanField(default=False)
    capacity = models.PositiveIntegerField(default=30)

    class Meta:
        verbose_name = "Grupo/Sección"
        verbose_name_plural = "Grupos/Secciones"
        unique_together = ("course", "section")

    def __str__(self):
        t = " (LAB)" if self.is_lab else ""
        return f"{self.course.code}-{self.section}{t}"

    @property
    def enrolled_count(self) -> int:
        return self.enrollments.count()

    @property
    def has_capacity(self) -> bool:
        return self.enrolled_count < self.capacity

# --- Matrículas ---
class Enrollment(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={"role__name": "Alumno"},
        related_name="enrollments",
    )
    course_group = models.ForeignKey(CourseGroup, on_delete=models.CASCADE, related_name="enrollments")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Matrícula"
        verbose_name_plural = "Matrículas"
        unique_together = ("student", "course_group")

    def clean(self):
        # Evita superar capacidad
        if not self.course_group.has_capacity and not self.pk:
            from django.core.exceptions import ValidationError
            raise ValidationError("Este grupo ya alcanzó su capacidad.")

    def __str__(self):
        return f"{self.student.username} -> {self.course_group}"

# --- Evaluaciones y Notas ---
class Assessment(models.Model):
    TYPE_CHOICES = [
        ("EX", "Examen"),
        ("PC", "Práctica/Control"),
        ("PR", "Proyecto"),
        ("OT", "Otro"),
    ]
    course_group = models.ForeignKey(CourseGroup, on_delete=models.CASCADE, related_name="assessments")
    title = models.CharField(max_length=120)
    kind = models.CharField(max_length=2, choices=TYPE_CHOICES, default="EX")
    weight = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # porcentaje
    total_points = models.DecimalField(max_digits=6, decimal_places=2, default=20)
    # Docente puede subir archivo (enunciado del examen, etc.)
    attachment = models.FileField(upload_to="exams/", blank=True, null=True)

    class Meta:
        verbose_name = "Evaluación"
        verbose_name_plural = "Evaluaciones"

    def __str__(self):
        return f"{self.course_group} - {self.title}"

class Grade(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={"role__name": "Alumno"},
        related_name="grades",
    )
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="grades")
    score = models.DecimalField(max_digits=6, decimal_places=2)
    uploaded_exam = models.FileField(upload_to="exam_uploads/", blank=True, null=True)  # PDF/Evidencia

    class Meta:
        verbose_name = "Nota"
        verbose_name_plural = "Notas"
        unique_together = ("student", "assessment")

    def __str__(self):
        return f"{self.student.username} - {self.assessment.title}: {self.score}"
