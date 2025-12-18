# apps/academics/views_teacher.py

from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Avg, Min, Max

from .models import (
    CourseGroup,
    Grade,
    Room,
    RoomReservation,
    CourseTopic,
    CourseMaterial,
    Assignment,
    AssignmentSubmission,
)

from .schedule_data import HORARIOS, normalize_day, normalize_time


def _is_teacher(user):
    return hasattr(user, "role") and user.role and user.role.name.lower() == "docente"


def _to_minutes(hhmm: str) -> int:
    dt = datetime.strptime(hhmm, "%H:%M")
    return dt.hour * 60 + dt.minute


def _slot_overlaps(sess_start: str, sess_end: str, slot_start: str, slot_end: str) -> bool:
    a1, a2 = _to_minutes(sess_start), _to_minutes(sess_end)
    b1, b2 = _to_minutes(slot_start), _to_minutes(slot_end)
    return a1 < b2 and a2 > b1


# --- PANEL PRINCIPAL DEL DOCENTE ---
@login_required
def teacher_dashboard(request):
    user = request.user
    if not _is_teacher(user):
        return redirect("users:login")

    groups = (
        CourseGroup.objects
        .filter(course__teacher=user)
        .select_related("course")
        .order_by("course__code", "section")
    )
    return render(request, "teacher/dashboard.html", {"groups": groups})


# --- TOMAR ASISTENCIA (lista de grupos) ---
@login_required
def teacher_attendance(request):
    user = request.user
    if not _is_teacher(user):
        return redirect("users:login")

    groups = (
        CourseGroup.objects
        .filter(course__teacher=user)
        .select_related("course")
        .order_by("course__code", "section")
    )
    return render(request, "teacher/attendance.html", {"groups": groups})


# --- NOTAS Y ESTADÍSTICAS ---
@login_required
def teacher_grades(request):
    user = request.user
    if not _is_teacher(user):
        return redirect("users:login")

    grades = (
        Grade.objects
        .select_related("assessment__course_group__course", "student")
        .filter(assessment__course_group__course__teacher=user)
    )

    stats = grades.aggregate(
        promedio=Avg("score"),
        minimo=Min("score"),
        maximo=Max("score"),
    )

    return render(request, "teacher/grades.html", {"grades": grades, "stats": stats})


# --- HORARIO DEL DOCENTE (grilla) ---
@login_required
def teacher_schedule(request):
    user = request.user
    if not _is_teacher(user):
        return redirect("users:login")

    weekdays = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes"]

    groups = (
        CourseGroup.objects
        .filter(course__teacher=user)
        .select_related("course")
        .order_by("course__code", "section")
    )

    # Slots base + slots que existan en el CSV para esos cursos (para que NUNCA quede vacío)
    base_slots = [
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
    slot_set = set(base_slots)

    # agrega slots reales del CSV del docente
    for g in groups:
        code = str(g.course.code).strip()
        section = str(g.section).strip().upper()
        for sess in HORARIOS.get((code, section), []):
            s = f"{normalize_time(sess['start'])}-{normalize_time(sess['end'])}"
            slot_set.add(s)

    # ordena slots por hora inicio
    def slot_key(slot):
        a, _ = slot.split("-")
        return _to_minutes(a)

    time_slots = sorted(slot_set, key=slot_key)

    schedule_table = {slot: {day: "" for day in weekdays} for slot in time_slots}

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

    teacher_name = user.get_full_name() or user.username
    teacher_str = f"<br><small>{teacher_name}</small>"

    for g in groups:
        course = g.course
        code = str(course.code).strip()
        section = str(g.section).strip().upper()
        key = (code, section)

        sessions = HORARIOS.get(key, [])
        if not sessions:
            continue

        if code not in course_colors:
            course_colors[code] = color_classes[color_index % len(color_classes)]
            color_index += 1
        color_class = course_colors[code]

        for sess in sessions:
            day = normalize_day(sess.get("day", ""))
            sess_start = normalize_time(sess.get("start", ""))
            sess_end = normalize_time(sess.get("end", ""))
            classroom = sess.get("classroom", "")

            if day not in weekdays or not sess_start or not sess_end:
                continue

            exact_slot = f"{sess_start}-{sess_end}"

            # si existe exacto, lo usa; si no, reparte por solapamiento
            matched_slots = []
            if exact_slot in time_slots:
                matched_slots = [exact_slot]
            else:
                for slot in time_slots:
                    s1, s2 = slot.split("-")
                    if _slot_overlaps(sess_start, sess_end, s1, s2):
                        matched_slots.append(slot)

            if not matched_slots:
                continue

            html = (
                f"<div class='p-1 {color_class}'>"
                f"<strong>{course.name}</strong><br>"
                f"<small>Cod. {code} - Sec. {section}</small><br>"
                f"<small>Aula {classroom}</small>"
                f"{teacher_str}"
                f"</div>"
            )

            for slot_label in matched_slots:
                if schedule_table[slot_label][day]:
                    schedule_table[slot_label][day] += "<hr class='my-1'/>" + html
                else:
                    schedule_table[slot_label][day] = html

    schedule_rows = [
        (slot, [schedule_table[slot][day] for day in weekdays])
        for slot in time_slots
    ]

    context = {
        "groups": groups,
        "weekdays": weekdays,
        "schedule_rows": schedule_rows,
    }
    return render(request, "teacher/schedule.html", context)


# --- RESERVA DE AMBIENTES ---
@login_required
def teacher_rooms(request):
    user = request.user
    if not _is_teacher(user):
        return redirect("users:login")

    rooms = Room.objects.all().order_by("floor", "number")
    my_reservations = RoomReservation.objects.filter(teacher=user).order_by("-date", "start_time")

    return render(request, "teacher/rooms.html", {"rooms": rooms, "reservations": my_reservations})


# --- DETALLE DE CURSO DEL DOCENTE ---
@login_required
def teacher_course_detail(request, group_id: int):
    user = request.user
    if not _is_teacher(user):
        return redirect("users:login")

    group = get_object_or_404(
        CourseGroup.objects.select_related("course"),
        pk=group_id,
        course__teacher=user,
    )

    materials = CourseMaterial.objects.filter(course_group=group).order_by("-created_at")
    topics = CourseTopic.objects.filter(course_group=group).order_by("week_number")

    return render(
        request,
        "teacher/course_detail.html",
        {"group": group, "materials": materials, "topics": topics},
    )


# --- DETALLE / CALIFICACIÓN DE TAREA ---
@login_required
def teacher_assignment_detail(request, assignment_id: int):
    user = request.user
    if not _is_teacher(user):
        return redirect("users:login")

    assignment = get_object_or_404(
        Assignment.objects.select_related("topic__course_group__course"),
        pk=assignment_id,
    )
    group = assignment.topic.course_group

    if group.course.teacher != user:
        return redirect("academics:teacher_dashboard")

    submissions = (
        AssignmentSubmission.objects
        .select_related("student")
        .filter(assignment=assignment)
        .order_by("uploaded_at")
    )

    if request.method == "POST":
        for sub in submissions:
            score_key = f"score_{sub.id}"
            feedback_key = f"feedback_{sub.id}"

            raw_score = (request.POST.get(score_key) or "").strip()
            feedback = (request.POST.get(feedback_key) or "").strip()

            if raw_score == "":
                sub.score = None
            else:
                try:
                    sub.score = float(raw_score)
                except ValueError:
                    pass

            sub.feedback = feedback
            sub.save()

        return redirect("academics:teacher_assignment_detail", assignment_id=assignment.id)

    return render(
        request,
        "teacher/assignment_detail.html",
        {"group": group, "assignment": assignment, "submissions": submissions},
    )
