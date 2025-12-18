# apps/academics/views_student.py

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Avg
from django.views.decorators.http import require_http_methods

from .schedule_data import HORARIOS, normalize_day, normalize_time

from .models import (
    Enrollment,
    Grade,
    CourseGroup,
    LabGroup,
    LabEnrollment,
    CourseTopic,
    Assignment,
    AssignmentSubmission,
)


def _is_student(user):
    """Devuelve True si el usuario tiene rol Alumno."""
    try:
        return hasattr(user, "role") and user.role and user.role.name.lower() == "alumno"
    except Exception:
        return False


def _normalize_slot(slot_value) -> str:
    """
    Convierte cualquier slot a formato 'HH:MM-HH:MM'
    - acepta '07:00-07:50', '07:00:00-07:50:00', etc.
    """
    s = str(slot_value).strip()
    if "-" in s:
        a, b = s.split("-", 1)
        return f"{normalize_time(a)}-{normalize_time(b)}"
    return s


def _busy_slots_for_student(user):
    """
    Devuelve un set de (day, slot) ocupados por teoría + laboratorios,
    para verificar cruces de horario.
    """
    busy = set()

    # --- Teoría ---
    enrollments = (
        Enrollment.objects
        .filter(student=user)
        .select_related("course_group__course")
    )

    for enr in enrollments:
        course = enr.course_group.course
        code = str(course.code).strip()
        section = str(enr.course_group.section).strip().upper()  # ✅ IMPORTANTE
        key = (code, section)

        for sess in HORARIOS.get(key, []):
            day = normalize_day(sess.get("day"))
            start = normalize_time(sess.get("start"))
            end = normalize_time(sess.get("end"))
            slot_label = f"{start}-{end}"
            if day and start and end:
                busy.add((day, slot_label))

    # --- Laboratorios ya inscritos ---
    lab_enrs = (
        LabEnrollment.objects
        .filter(student=user)
        .select_related("lab_group")
    )
    for le in lab_enrs:
        lg = le.lab_group
        day = normalize_day(lg.day)
        slot_label = _normalize_slot(lg.slot)
        if day and slot_label:
            busy.add((day, slot_label))

    return busy


# =========================
# PANEL DEL ALUMNO (INICIO)
# =========================
@login_required
def student_dashboard(request):
    user = request.user
    if not _is_student(user):
        return redirect("users:login")

    enrollments_qs = (
        Enrollment.objects
        .filter(student=user)
        .select_related("course_group__course")
        .order_by("course_group__course__name")
    )
    enrollment_count = enrollments_qs.count()
    latest_enrollments = enrollments_qs[:5]

    latest_grades = (
        Grade.objects
        .filter(student=user)
        .select_related("assessment__course_group__course")
        .order_by("-assessment__id")
    )

    overall_average = (
        Grade.objects
        .filter(student=user)
        .aggregate(promedio=Avg("score"))
        .get("promedio")
    )

    context = {
        "latest_enrollments": latest_enrollments,
        "latest_grades": latest_grades,
        "overall_average": overall_average,
        "enrollment_count": enrollment_count,
    }
    return render(request, "student/dashboard.html", context)


# ==============  MIS CURSOS  ==============
@login_required
def student_courses(request):
    user = request.user
    if not _is_student(user):
        return redirect("users:login")

    enrollments = (
        Enrollment.objects
        .filter(student=user)
        .select_related(
            "course_group",
            "course_group__course",
            "course_group__course__teacher",
        )
        .order_by("course_group__course__code", "course_group__section")
    )

    return render(request, "student/courses.html", {"enrollments": enrollments})


@login_required
def student_course_detail(request, group_id):
    user = request.user
    if not _is_student(user):
        return redirect("users:login")

    group = get_object_or_404(
        CourseGroup.objects.select_related("course", "course__teacher"),
        pk=group_id,
    )

    # Verificamos matrícula del alumno en ese grupo
    if not Enrollment.objects.filter(student=user, course_group=group).exists():
        return redirect("academics:student_courses")

    # Materiales (si hay related_name="materials")
    materials = []
    try:
        materials_manager = getattr(group, "materials", None)
        if materials_manager is not None and hasattr(materials_manager, "all"):
            materials = materials_manager.all()
    except Exception:
        materials = []

    grades = (
        Grade.objects
        .filter(student=user, assessment__course_group=group)
        .select_related("assessment")
        .order_by("assessment__id")
    )

    topics = (
        CourseTopic.objects
        .filter(course_group=group)
        .order_by("week_number")
    )

    context = {
        "group": group,
        "materials": materials,
        "grades": grades,
        "topics": topics,
    }
    return render(request, "student/course_detail.html", context)


# ==========  HORARIO (teoría + laboratorios)  ==========
@login_required
def student_schedule(request):
    user = request.user
    if not _is_student(user):
        return redirect("users:login")

    weekdays = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes"]
    time_slots = [
        "07:00-07:50",
        "07:50-08:40",
        "08:50-09:40",
        "09:40-10:30",
        "10:40-11:30",
        "11:30-12:20",
        "12:20-13:10",
        "13:10-14:00",
        "14:00-14:50",
        "14:50-15:40",
        "15:50-16:40",
        "16:40-17:30",
        "17:40-18:30",
        "18:30-19:20",
    ]

    schedule_table = {slot: {day: "" for day in weekdays} for slot in time_slots}

    enrollments = (
        Enrollment.objects
        .filter(student=user)
        .select_related("course_group__course", "course_group__course__teacher")
    )

    color_classes = [
        "bg-light",
        "table-primary",
        "table-success",
        "table-warning",
        "table-info",
        "table-danger",
        "table-secondary",
    ]
    course_colors = {}
    color_index = 0

    # ---- Teoría ----
    for enr in enrollments:
        course = enr.course_group.course
        code = str(course.code).strip()
        section = str(enr.course_group.section).strip().upper()  # ✅ IMPORTANTE
        key = (code, section)

        sessions = HORARIOS.get(key, [])
        if not sessions:
            continue

        if code not in course_colors:
            course_colors[code] = color_classes[color_index % len(color_classes)]
            color_index += 1
        color_class = course_colors[code]

        teacher = getattr(course, "teacher", None)
        teacher_str = ""
        if teacher:
            full_name = teacher.get_full_name()
            display_name = full_name if full_name else teacher.username
            teacher_str = f"<br><small>{display_name}</small>"

        for sess in sessions:
            day = normalize_day(sess.get("day"))
            start = normalize_time(sess.get("start"))
            end = normalize_time(sess.get("end"))
            slot_label = f"{start}-{end}"

            if day not in weekdays or slot_label not in time_slots:
                continue

            html = (
                f"<div class='p-1 {color_class}'>"
                f"<strong>{course.name}</strong><br>"
                f"<small>Cod. {code} - Sec. {section}</small><br>"
                f"<small>Aula {sess.get('classroom','')}</small>"
                f"{teacher_str}"
                f"</div>"
            )
            schedule_table[slot_label][day] = html

    # ---- Laboratorios ----
    lab_enrollments = (
        LabEnrollment.objects
        .filter(student=user)
        .select_related("lab_group__course")
    )

    for le in lab_enrollments:
        lab = le.lab_group
        course = lab.course
        code = str(course.code).strip()

        if code not in course_colors:
            course_colors[code] = color_classes[color_index % len(color_classes)]
            color_index += 1
        color_class = course_colors[code]

        day = normalize_day(lab.day)
        slot_label = _normalize_slot(lab.slot)

        if day not in weekdays or slot_label not in time_slots:
            continue

        extra = ""
        if schedule_table[slot_label][day]:
            extra = schedule_table[slot_label][day] + "<hr class='my-1'/>"

        html = (
            f"{extra}"
            f"<div class='p-1 {color_class}'>"
            f"<strong>{course.name} (Laboratorio)</strong><br>"
            f"<small>Opción {lab.code} - Cod. {code}</small><br>"
            f"<small>{day} {slot_label} - {lab.classroom}</small>"
            f"</div>"
        )
        schedule_table[slot_label][day] = html

    schedule_rows = [
        (slot, [schedule_table[slot][day] for day in weekdays])
        for slot in time_slots
    ]

    return render(
        request,
        "student/schedule.html",
        {"weekdays": weekdays, "schedule_rows": schedule_rows},
    )


# ==========  MIS NOTAS  ==========
@login_required
def student_grades(request):
    user = request.user
    if not _is_student(user):
        return redirect("users:login")

    grades_qs = (
        Grade.objects
        .filter(student=user)
        .select_related("assessment__course_group__course")
        .order_by("-assessment__id")
    )

    return render(request, "student/grades.html", {"grades": grades_qs})


# =============  OFERTAS / MATRICULARME (teoría)  =============
@login_required
def student_offerings(request):
    user = request.user
    if not _is_student(user):
        return redirect("users:login")

    enrolled_group_ids = set(
        Enrollment.objects
        .filter(student=user)
        .values_list("course_group_id", flat=True)
    )

    groups = (
        CourseGroup.objects
        .select_related("course", "course__teacher")
        .order_by("course__code", "section")
    )

    return render(
        request,
        "student/offerings.html",
        {"groups": groups, "enrolled_group_ids": enrolled_group_ids},
    )


@login_required
def student_enroll(request, group_id):
    user = request.user
    if not _is_student(user):
        return redirect("users:login")

    if request.method != "POST":
        return redirect("academics:student_offerings")

    group = get_object_or_404(CourseGroup, pk=group_id)
    Enrollment.objects.get_or_create(student=user, course_group=group)

    return redirect("academics:student_offerings")


# ==============================  LABORATORIOS  ==============================
@login_required
def student_lab_offerings(request):
    user = request.user
    if not _is_student(user):
        return redirect("users:login")

    enrolled_course_ids = (
        Enrollment.objects
        .filter(student=user)
        .values_list("course_group__course_id", flat=True)
    )

    labs = (
        LabGroup.objects
        .filter(course_id__in=enrolled_course_ids)
        .select_related("course")
        .order_by("course__code", "code")
    )

    my_lab_enrollments = LabEnrollment.objects.filter(student=user)
    my_lab_ids = {le.lab_group_id for le in my_lab_enrollments}
    courses_with_lab_selected = {le.lab_group.course_id for le in my_lab_enrollments}

    return render(
        request,
        "student/labs.html",
        {
            "labs": labs,
            "my_lab_ids": my_lab_ids,
            "courses_with_lab_selected": courses_with_lab_selected,
        },
    )


@login_required
def student_lab_enroll(request, lab_id):
    user = request.user
    if not _is_student(user):
        return redirect("users:login")

    if request.method != "POST":
        return redirect("academics:student_lab_offerings")

    lab = get_object_or_404(LabGroup.objects.select_related("course"), pk=lab_id)

    if not Enrollment.objects.filter(student=user, course_group__course=lab.course).exists():
        messages.error(request, "No estás matriculado en el curso de este laboratorio.")
        return redirect("academics:student_lab_offerings")

    if LabEnrollment.objects.filter(student=user, lab_group__course=lab.course).exists():
        messages.error(request, "Ya estás inscrito en un laboratorio de este curso.")
        return redirect("academics:student_lab_offerings")

    if lab.seats_left <= 0:
        messages.error(request, "Este laboratorio ya no tiene cupos disponibles.")
        return redirect("academics:student_lab_offerings")

    busy = _busy_slots_for_student(user)

    day = normalize_day(lab.day)
    slot_label = _normalize_slot(lab.slot)

    if (day, slot_label) in busy:
        messages.error(request, "No puedes inscribirte: cruce de horario.")
        return redirect("academics:student_lab_offerings")

    LabEnrollment.objects.get_or_create(student=user, lab_group=lab)
    messages.success(request, "Te has inscrito en el laboratorio correctamente.")
    return redirect("academics:student_lab_offerings")


@login_required
def student_lab_unenroll(request, lab_id):
    user = request.user
    if not _is_student(user):
        return redirect("users:login")

    if request.method != "POST":
        return redirect("academics:student_lab_offerings")

    lab = get_object_or_404(LabGroup, pk=lab_id)

    deleted, _ = LabEnrollment.objects.filter(student=user, lab_group=lab).delete()

    if deleted:
        messages.success(request, "Has sido desinscrito del laboratorio.")
    else:
        messages.info(request, "No estabas inscrito en este laboratorio.")

    return redirect("academics:student_lab_offerings")


# ==============================  VER / SUBIR TAREA  ==============================
@login_required
@require_http_methods(["GET", "POST"])
def student_assignment_view(request, assignment_id):
    user = request.user
    if not _is_student(user):
        return redirect("users:login")

    assignment = get_object_or_404(
        Assignment.objects.select_related(
            "topic__course_group__course",
            "topic__course_group__course__teacher",
        ),
        pk=assignment_id,
    )
    group = assignment.topic.course_group

    if not Enrollment.objects.filter(student=user, course_group=group).exists():
        messages.error(request, "No estás matriculado en este curso.")
        return redirect("academics:student_courses")

    submission = AssignmentSubmission.objects.filter(
        assignment=assignment,
        student=user
    ).first()

    if request.method == "POST":
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            messages.error(request, "Debes seleccionar un archivo para subir.")
        else:
            if submission is None:
                submission = AssignmentSubmission.objects.create(
                    assignment=assignment,
                    student=user,
                    file=uploaded_file,
                )
            else:
                submission.file = uploaded_file
                submission.save()

            messages.success(request, "Tu entrega se ha subido correctamente.")
            return redirect("academics:student_assignment_view", assignment_id=assignment.id)

    return render(
        request,
        "student/assignment_detail.html",
        {"assignment": assignment, "group": group, "submission": submission},
    )
