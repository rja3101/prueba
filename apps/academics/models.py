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
        null=True,
        blank=True,
    )

    semester = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Número de semestre (1, 2, 3, ...)."
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
    course_group = models.ForeignKey(
        CourseGroup,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
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
    course_group = models.ForeignKey(
        CourseGroup,
        on_delete=models.CASCADE,
        related_name="assessments",
    )
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
    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.CASCADE,
        related_name="grades",
    )
    score = models.DecimalField(max_digits=6, decimal_places=2)
    uploaded_exam = models.FileField(
        upload_to="exam_uploads/",
        blank=True,
        null=True,
    )  # PDF/Evidencia

    class Meta:
        verbose_name = "Nota"
        verbose_name_plural = "Notas"
        unique_together = ("student", "assessment")

    def __str__(self):
        return f"{self.student.username} - {self.assessment.title}: {self.score}"


# --- Asistencia ---
class Attendance(models.Model):
    course_group = models.ForeignKey(
        CourseGroup,
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={"role__name": "Alumno"},
    )
    date = models.DateField(auto_now_add=True)
    present = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Asistencia"
        verbose_name_plural = "Asistencias"
        unique_together = ("course_group", "student", "date")

    def __str__(self):
        return f"{self.course_group} - {self.student.username} ({'Presente' if self.present else 'Ausente'})"


# --- Materiales de curso/grupo ---
class CourseMaterial(models.Model):
    course_group = models.ForeignKey(
        CourseGroup,
        on_delete=models.CASCADE,
        related_name="materials",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to="materials/", blank=True, null=True)
    link = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Material de curso"
        verbose_name_plural = "Materiales de curso"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.course_group} - {self.title}"


# --- Ambientes (aulas y laboratorios) ---
class Room(models.Model):
    number = models.CharField(max_length=10, unique=True)
    floor = models.PositiveSmallIntegerField(default=1)
    is_lab = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Ambiente/Aula"
        verbose_name_plural = "Ambientes/Aulas"

    def __str__(self):
        return f"Aula {self.number} {'(Lab)' if self.is_lab else ''}"


class RoomReservation(models.Model):
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={"role__name": "Docente"},
        related_name="reservations",
    )
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    purpose = models.CharField(max_length=120, blank=True)

    class Meta:
        verbose_name = "Reserva de ambiente"
        verbose_name_plural = "Reservas de ambientes"
        unique_together = ("room", "date", "start_time", "end_time")

    def __str__(self):
        return f"{self.room.number} - {self.teacher.username} ({self.date})"

from django.conf import settings
from django.db import models

User = settings.AUTH_USER_MODEL


DAY_CHOICES = [
    ("Lunes", "Lunes"),
    ("Martes", "Martes"),
    ("Miercoles", "Miercoles"),
    ("Jueves", "Jueves"),
    ("Viernes", "Viernes"),
]


class LabGroup(models.Model):
    """
    Grupo de laboratorio (A, B, C) asociado a un curso.
    No depende de CourseGroup (teoría), solo del Course.
    """
    course = models.ForeignKey(
        "academics.Course",
        on_delete=models.CASCADE,
        related_name="lab_groups",
    )
    code = models.CharField(max_length=2)  # 'A', 'B', 'C'
    day = models.CharField(max_length=10, choices=DAY_CHOICES)
    slot = models.CharField(max_length=11)  # '07:00-07:50', etc.
    classroom = models.CharField(max_length=20, blank=True)
    capacity = models.PositiveIntegerField(default=20)

    class Meta:
        unique_together = ("course", "code")

    def __str__(self):
        return f"Lab {self.course.code} - {self.code} ({self.day} {self.slot})"

    @property
    def seats_used(self):
        return self.enrollments.count()

    @property
    def seats_left(self):
        return max(0, self.capacity - self.seats_used)


class LabEnrollment(models.Model):
    """
    Matrícula de un alumno en un grupo de laboratorio.
    """
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="lab_enrollments",
    )
    lab_group = models.ForeignKey(
        LabGroup,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "lab_group")

    def __str__(self):
        return f"{self.student} -> {self.lab_group}"

# apps/academics/models.py
from django.conf import settings
from django.db import models

# ... ya tienes CourseGroup, etc.

class CourseTopic(models.Model):
    """
    Tema de una semana del curso (Semana 1, Semana 2, etc.).
    Se asocia a un CourseGroup específico.
    """
    course_group = models.ForeignKey(
        "CourseGroup",
        on_delete=models.CASCADE,
        related_name="topics",
    )
    week_number = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["week_number"]
        unique_together = ("course_group", "week_number")

    def __str__(self):
        return f"{self.course_group} - Semana {self.week_number}: {self.title}"


class Assignment(models.Model):
    """
    Tarea asociada a un tema específico.
    """
    topic = models.ForeignKey(
        CourseTopic,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField(null=True, blank=True)

    resource_file = models.FileField(
        upload_to="assignments/resources/",
        null=True,
        blank=True,
        help_text="Archivo que sube el docente (enunciado, PDF, etc.).",
    )
    resource_link = models.URLField(
        blank=True,
        help_text="Link externo (Codeforces, hoja de problemas, etc.).",
    )

    def __str__(self):
        return f"{self.topic} - {self.title}"


class AssignmentFile(models.Model):
    """
    Archivos que sube el profesor para la tarea
    (enunciado, PDFs, ejemplos, etc.).
    """
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="files",
    )
    file = models.FileField(upload_to="assignments/files/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Archivo de {self.assignment}"


class AssignmentSubmission(models.Model):
    """
    Entrega del alumno: archivo, comentario, nota, feedback.
    """
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assignment_submissions",
    )
    file = models.FileField(upload_to="assignments/submissions/")
    comment = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    grade = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    feedback = models.TextField(blank=True)
    graded_at = models.DateTimeField(null=True, blank=True)
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="graded_assignment_submissions",
    )

    class Meta:
        unique_together = ("assignment", "student")

    def __str__(self):
        return f"{self.assignment} - {self.student}"

class AssignmentSubmission(models.Model):
    assignment = models.ForeignKey(
        "Assignment",
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assignment_submissions",
    )
    file = models.FileField(upload_to="assignments/submissions/")
    submitted_at = models.DateTimeField(auto_now_add=True)

    # Nota que pondrá el docente (opcional)
    grade = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    feedback = models.TextField(blank=True)

    class Meta:
        unique_together = ("assignment", "student")

    def __str__(self):
        return f"{self.assignment} - {self.student}"
