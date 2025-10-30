from django.db import models
from django.conf import settings

DAYS = [
    ("LUN", "Lunes"), ("MAR", "Martes"), ("MIE", "Miércoles"),
    ("JUE", "Jueves"), ("VIE", "Viernes"), ("SAB", "Sábado"),
]

class Schedule(models.Model):
    course_group = models.ForeignKey("academics.CourseGroup", on_delete=models.CASCADE, related_name="schedules")
    day = models.CharField(max_length=3, choices=DAYS)
    start_time = models.TimeField()
    end_time = models.TimeField()
    classroom = models.CharField(max_length=50)

    class Meta:
        verbose_name = "Horario"
        verbose_name_plural = "Horarios"
        constraints = [
            models.CheckConstraint(check=models.Q(end_time__gt=models.F("start_time")), name="end_after_start"),
        ]
        unique_together = ("course_group", "day", "start_time", "end_time", "classroom")

    def __str__(self):
        return f"{self.course_group} {self.day} {self.start_time}-{self.end_time} {self.classroom}"

class Session(models.Model):
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name="sessions")
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Sesión"
        verbose_name_plural = "Sesiones"
        unique_together = ("schedule", "date")

    def __str__(self):
        return f"{self.schedule} @ {self.date}"

class Attendance(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        limit_choices_to={"role__name": "Alumno"}, related_name="attendances"
    )
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="attendances")
    entry_time = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField()

    class Meta:
        verbose_name = "Asistencia"
        verbose_name_plural = "Asistencias"
        unique_together = ("student", "session")

    def __str__(self):
        return f"{self.student} @ {self.session}"
