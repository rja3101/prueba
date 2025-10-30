# apps/academics/views_stats.py
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.shortcuts import render, get_object_or_404

# TODO: ajusta imports según tus modelos
from .models import CourseGroup, Grade
from attendance.models import AttendanceRecord

@login_required
def group_stats(request, group_id: int):
    """
    Estadísticas simples del grupo:
    - Promedio por evaluación
    - Promedio global
    - % asistencia (si hay AttendanceRecord)
    """
    group = get_object_or_404(CourseGroup, id=group_id)

    # Promedio por assessment
    by_assessment = (
        Grade.objects
        .filter(assessment__group=group)
        .values("assessment__name")
        .annotate(avg=Avg("value"), n=Count("id"))
        .order_by("assessment__name")
    )

    # Promedio global
    overall = Grade.objects.filter(assessment__group=group).aggregate(avg=Avg("value"))

    # % asistencia (presente o tarde cuentan como asistencia)
    total_att = AttendanceRecord.objects.filter(session__group=group).count()
    present_like = AttendanceRecord.objects.filter(
        session__group=group, status__in=["present", "late"]
    ).count()
    attendance_pct = (present_like * 100.0 / total_att) if total_att else None

    ctx = {
        "group": group,
        "by_assessment": by_assessment,
        "overall": overall["avg"],
        "attendance_pct": attendance_pct,
    }
    return render(request, "academics/group_stats.html", ctx)
