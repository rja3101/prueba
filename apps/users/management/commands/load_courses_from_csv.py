import csv
from pathlib import Path

from django.apps import apps
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()

# Intentamos obtener los modelos sin romper si cambian de nombre
Course = apps.get_model("academics", "Course")
CourseGroup = apps.get_model("academics", "CourseGroup", require_ready=False)


class Command(BaseCommand):
    help = (
        "Carga cursos desde un CSV con columnas: "
        "code,name,semester,credits,teacher_username"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_path",
            type=str,
            help="Ruta al archivo CSV de cursos (por ejemplo: data/cursos.csv)",
        )

        parser.add_argument(
            "--section",
            type=str,
            default="A",
            help="Sección por defecto para crear el grupo (CourseGroup), por defecto 'A'.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])
        default_section = options["section"]

        if not csv_path.exists():
            self.stderr.write(self.style.ERROR(f"El archivo {csv_path} no existe"))
            return

        if Course is None:
            self.stderr.write(
                self.style.ERROR("No se encontró el modelo academics.Course")
            )
            return

        if CourseGroup is None:
            self.stdout.write(
                self.style.WARNING(
                    "No se encontró el modelo CourseGroup; "
                    "solo se crearán Course, sin grupos/secciones."
                )
            )

        created_courses = 0
        updated_courses = 0
        created_groups = 0
        skipped_groups = 0

        with csv_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                code = row["code"].strip()
                name = row["name"].strip()
                semester = int(row["semester"])
                credits = int(row["credits"])
                teacher_username = row.get("teacher_username", "").strip()

                # Crear/actualizar Course
                course, created = Course.objects.get_or_create(
                    code=code,
                    defaults={
                        "name": name,
                        "semester": semester,
                        "credits": credits,
                    },
                )

                if created:
                    created_courses += 1
                    self.stdout.write(self.style.SUCCESS(f"Creado curso: {code} - {name}"))
                else:
                    # Actualizamos datos básicos por si cambiaron
                    course.name = name
                    course.semester = semester
                    course.credits = credits
                    course.save()
                    updated_courses += 1
                    self.stdout.write(
                        self.style.WARNING(f"Actualizado curso existente: {code} - {name}")
                    )

                # Si existe CourseGroup, intentamos crear una sección
                if CourseGroup is not None and teacher_username:
                    try:
                        teacher = User.objects.get(username=teacher_username)
                    except User.DoesNotExist:
                        skipped_groups += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f"Docente '{teacher_username}' no encontrado; "
                                f"NO se crea grupo para curso {code}."
                            )
                        )
                        continue

                    # Dependiendo de cómo sea tu modelo CourseGroup, ajusta los nombres de campos:
                    group, cg_created = CourseGroup.objects.get_or_create(
                        course=course,
                        section=default_section,
                        teacher=teacher,
                    )

                    if cg_created:
                        created_groups += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Creado grupo para {code} sección {default_section} "
                                f"con docente {teacher.username}"
                            )
                        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Cursos: creados {created_courses}, actualizados {updated_courses}"
            )
        )

        if CourseGroup is not None:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Grupos: creados {created_groups}, omitidos (sin docente) {skipped_groups}"
                )
            )
