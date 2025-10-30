from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Max, Min
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404
from .models import CourseGroup, Grade

@login_required
def academics_index(request):
    """
    Página de inicio del módulo Académico:
    - Lista todos los grupos/secciones con conteo de matriculados.
    - Accesos a estadísticas (HTML) y exportar notas (CSV).
    """
    groups = (
        CourseGroup.objects
        .select_related("course", "course__teacher")
        .order_by("course__code", "section")
    )
    return render(request, "academics/index.html", {"groups": groups})

# --- Estadísticas en JSON (prom, máx, mín) ---
@login_required
def coursegroup_stats(request, group_id: int):
    cg = get_object_or_404(CourseGroup.objects.select_related("course"), pk=group_id)
    enrolled = cg.enrolled_count
    stats = (
        Grade.objects.filter(assessment__course_group=cg)
        .aggregate(avg=Avg("score"), mx=Max("score"), mn=Min("score"))
    )
    return JsonResponse({
        "course": cg.course.code,
        "group": cg.section,
        "enrolled": enrolled,
        "stats": {
            "avg": float(stats["avg"] or 0),
            "max": float(stats["mx"] or 0),
            "min": float(stats["mn"] or 0),
        },
    })

# --- Página HTML con gráfico de barras ---
@login_required
def group_stats_view(request, group_id: int):
    cg = get_object_or_404(CourseGroup.objects.select_related("course"), pk=group_id)
    enrolled = cg.enrolled_count
    stats = Grade.objects.filter(assessment__course_group=cg).aggregate(
        avg=Avg("score"), mx=Max("score"), mn=Min("score")
    )
    rows = (
        Grade.objects
        .filter(assessment__course_group=cg)
        .select_related("student", "assessment")
        .order_by("student__username")
    )
    labels = [f"{g.student.username}-{g.assessment.title}" for g in rows]
    scores = [float(g.score) for g in rows]
    ctx = {
        "course_group": cg,
        "enrolled": enrolled,
        "stats": stats,
        "labels": labels,
        "scores": scores,
    }
    return render(request, "academics/group_stats.html", ctx)

# --- Desempeño del alumno logueado (JSON) ---
@login_required
def my_performance(request):
    qs = (
        Grade.objects
        .filter(student=request.user)
        .select_related(
            "assessment",
            "assessment__course_group",
            "assessment__course_group__course"
        )
    )
    resumen = {}
    for g in qs:
        key = f"{g.assessment.course_group.course.code}-{g.assessment.course_group.section}"
        resumen.setdefault(key, {"items": [], "avg": 0})
        resumen[key]["items"].append({"assessment": g.assessment.title, "score": float(g.score)})
    for k, v in resumen.items():
        if v["items"]:
            v["avg"] = sum(i["score"] for i in v["items"]) / len(v["items"])
    return JsonResponse(resumen)

# --- Exportar notas del grupo a CSV ---
@login_required
def export_group_grades_csv(request, group_id: int):
    """
    Exporta a CSV las notas del grupo (una fila por (alumno, evaluación)).
    Columnas: username, curso, seccion, evaluacion, score
    """
    cg = get_object_or_404(CourseGroup.objects.select_related("course"), pk=group_id)
    rows = (
        Grade.objects
        .filter(assessment__course_group=cg)
        .select_related("student", "assessment")
        .order_by("student__username", "assessment__title")
    )

    # Construir CSV en memoria
    lines = ["username,curso,seccion,evaluacion,score"]
    for g in rows:
        uname = g.student.username.replace(",", " ")
        curso = cg.course.code
        secc = cg.section
        evalt = g.assessment.title.replace(",", " ")
        lines.append(f"{uname},{curso},{secc},{evalt},{float(g.score)}")

    content = "\n".join(lines)
    response = HttpResponse(content, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="notas_{cg.course.code}_{cg.section}.csv"'
    return response
