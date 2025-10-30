import io, pandas as pd
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import UploadFileForm
from .models import CourseGroup, Assessment, Grade

def is_teacher(u): return hasattr(u,"role") and u.role and u.role.name=="Docente"

@login_required @user_passes_test(is_teacher)
def import_grades(request, group_id:int):
    cg = get_object_or_404(CourseGroup, pk=group_id)
    if request.method == "POST":
        df = pd.read_excel(io.BytesIO(request.FILES["file"].read()))
        req = ["username","assessment_title","kind","score","total_points"]
        if not all(c in df.columns for c in req): messages.error(request,"Columnas requeridas: "+", ".join(req)); return redirect("import_grades",group_id=group_id)
        ok=upd=err=0
        for _,r in df.iterrows():
            try:
                uname = str(r["username"]).strip()
                student_id = cg.enrollments.filter(student__username=uname).values_list("student", flat=True).first()
                if not student_id: err+=1; continue
                ass,_ = Assessment.objects.get_or_create(course_group=cg, title=str(r["assessment_title"]).strip(),
                                                         defaults={"kind":str(r["kind"]).strip()[:2], "total_points": float(r["total_points"])})
                g, created = Grade.objects.update_or_create(student_id=student_id, assessment=ass, defaults={"score": float(r["score"])})
                ok += 1 if created else 0; upd += 0 if created else 1
            except: err+=1
        messages.success(request, f"Notas: nuevas={ok}, actualizadas={upd}, errores={err}")
        return redirect("coursegroup_stats_view", group_id=group_id)
    return render(request,"teacher/import_grades.html",{"form":UploadFileForm(),"group":cg})

@login_required @user_passes_test(is_teacher)
def grades_csv(request, group_id:int):
    cg = get_object_or_404(CourseGroup, pk=group_id)
    rows = ["username,curso,seccion,evaluacion,score"]
    qs = (Grade.objects.filter(assessment__course_group=cg)
          .select_related("student","assessment"))
    for g in qs:
        rows.append(f"{g.student.username},{cg.course.code},{cg.section},{g.assessment.title},{g.score}")
    resp = HttpResponse("\n".join(rows), content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"]=f'attachment; filename="notas_{cg.course.code}_{cg.section}.csv"'
    return resp
