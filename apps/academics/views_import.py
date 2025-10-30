import io, pandas as pd
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import get_user_model
from .forms import UploadFileForm
from apps.users.models import Role
from .models import CourseGroup, Enrollment
def is_staff(u): return u.is_staff

@login_required @user_passes_test(is_staff)
def import_students(request):
    if request.method == "POST":
        f = request.FILES["file"].read()
        df = pd.read_excel(io.BytesIO(f))
        for c in ["username","first_name","last_name","email"]:
            if c not in df.columns: messages.error(request,f"Falta {c}"); return redirect("import_students")
        User = get_user_model(); rol,_=Role.objects.get_or_create(name="Alumno")
        created=updated=errors=0
        for _,r in df.iterrows():
            try:
                u,cr = User.objects.get_or_create(username=str(r["username"]).strip(), defaults={
                    "first_name":str(r["first_name"]).strip(),"last_name":str(r["last_name"]).strip(),
                    "email":str(r["email"]).strip(),"role":rol,"is_active":True})
                if cr: u.set_password("123"); u.save(); created+=1
                else: updated+=1
            except: errors+=1
        messages.success(request,f"Alumnos: creados={created}, actualizados={updated}, errores={errors}")
        return redirect("import_students")
    return render(request,"secretary/import_students.html",{"form":UploadFileForm()})

@login_required @user_passes_test(is_staff)
def import_enrollments(request):
    if request.method == "POST":
        f = request.FILES["file"].read()
        df = pd.read_excel(io.BytesIO(f))
        for c in ["username","course_code","section"]:
            if c not in df.columns: messages.error(request,f"Falta {c}"); return redirect("import_enrollments")
        User = get_user_model(); ok=wlist=err=0
        for _,r in df.iterrows():
            try:
                u = User.objects.get(username=str(r["username"]).strip())
                cg = CourseGroup.objects.select_related("course").get(course__code=str(r["course_code"]).strip(),
                                                                     section=str(r["section"]).strip())
                # versión simple: crear Enrollment si hay cupo, sino ignorar (o agregar a waitlist si la tienes)
                if cg.enrolled_count < cg.capacity:
                    Enrollment.objects.get_or_create(student=u, course_group=cg); ok+=1
                else: wlist+=1
            except: err+=1
        messages.success(request,f"Matrículas: ok={ok}, sin_cupo={wlist}, errores={err}")
        return redirect("import_enrollments")
    return render(request,"secretary/import_enrollments.html",{"form":UploadFileForm()})
