from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.http import HttpResponse
from .models import CourseGroup
def is_staff(u): return u.is_staff

@login_required @user_passes_test(is_staff)
def occupancy_report(request):
    rows = [{"course":g.course.code,"name":g.course.name,"section":g.section,
             "cap":g.capacity,"used":g.enrolled_count,
             "pct": round((g.enrolled_count/g.capacity*100) if g.capacity else 0,2)}
            for g in CourseGroup.objects.select_related("course").all().order_by("course__code","section")]
    return render(request,"secretary/occupancy.html",{"rows":rows})

@login_required @user_passes_test(is_staff)
def occupancy_csv(request):
    lines = ["curso,nombre,seccion,capacidad,matriculados,porcentaje"]
    for g in CourseGroup.objects.select_related("course"):
        pct = (g.enrolled_count/g.capacity*100) if g.capacity else 0
        lines.append(f"{g.course.code},{g.course.name.replace(',',' ')},{g.section},{g.capacity},{g.enrolled_count},{pct:.2f}")
    resp = HttpResponse("\n".join(lines), content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"]='attachment; filename="ocupacion_secciones.csv"'
    return resp
