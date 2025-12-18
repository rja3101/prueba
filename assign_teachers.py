import csv
from pathlib import Path

from django.conf import settings
from apps.academics.models import Course
from apps.users.models import User


def find_teacher(teacher_key: str):
    """
    Busca un docente usando:
    - email
    - username
    - parte local del email como username (lo_mismo de lo_mismo@unsa.edu.pe)
    """
    teacher_key = (teacher_key or "").strip()
    if not teacher_key:
        return None

    lookups = []

    # 1) correo exacto
    lookups.append({"email__iexact": teacher_key})

    # 2) username exacto
    lookups.append({"username__iexact": teacher_key})

    # 3) si parece correo, parte antes de @ como username
    if "@" in teacher_key:
        local_part = teacher_key.split("@", 1)[0]
        lookups.append({"username__iexact": local_part})

    for lookup in lookups:
        try:
            return User.objects.get(**lookup)
        except User.DoesNotExist:
            continue

    return None


csv_path = Path(settings.BASE_DIR) / "data" / "cursos_con_docentes.csv"
print("Leyendo:", csv_path)

updated = 0
not_found_courses = 0
not_found_teachers = 0

with csv_path.open(newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        code = (row.get("code") or "").strip()
        teacher_key = (row.get("teacher_username") or "").strip()

        if not code or not teacher_key:
            continue

        # Buscar curso por código
        try:
            course = Course.objects.get(code=code)
        except Course.DoesNotExist:
            print(f"[WARN] Curso {code} no existe en la BD, lo salto.")
            not_found_courses += 1
            continue

        # Buscar docente con la lógica nueva
        teacher = find_teacher(teacher_key)
        if teacher is None:
            print(f"[WARN] No encontré usuario '{teacher_key}' para el curso {code}.")
            not_found_teachers += 1
            continue

        # Asignar y guardar
        course.teacher = teacher
        course.save()
        updated += 1
        print(
            f"[OK] {code} -> {teacher.get_full_name() or teacher.username} "
            f"({teacher.email})"
        )

print("==== RESUMEN ====")
print("Cursos actualizados:", updated)
print("Cursos no encontrados:", not_found_courses)
print("Docentes no encontrados:", not_found_teachers)
