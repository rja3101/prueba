import csv
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.academics.models import Course, CourseGroup
from apps.users.models import User


class Command(BaseCommand):
    help = "Crea grupos A y B para cada curso, asignando docentes desde el CSV."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str, help="Ruta al archivo cursos.csv")

    def handle(self, *args, **options):
        csv_path = options["csv_path"]

        created_count = 0
        skipped = 0

        with open(csv_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                code = row["code"].strip()
                teacher_username = row["teacher_username"].strip()

                try:
                    course = Course.objects.get(code=code)
                except Course.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f" Curso {code} no encontrado."))
                    skipped += 1
                    continue

                try:
                    teacher = User.objects.get(username=teacher_username)
                except User.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f" Docente '{teacher_username}' no encontrado."))
                    skipped += 1
                    continue

                # Crear secciones A y B si no existen
                for section in ["A", "B"]:
                    group, created = CourseGroup.objects.get_or_create(
                        course=course,
                        section=section,
                    )
                    if created:
                        created_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f" Creado grupo {course.code}-{section} ({teacher.username})")
                        )
                    else:
                        self.stdout.write(f" Grupo {course.code}-{section} ya existe.")

        self.stdout.write(
            self.style.SUCCESS(f"Proceso finalizado. Grupos creados: {created_count}, omitidos: {skipped}")
        )
