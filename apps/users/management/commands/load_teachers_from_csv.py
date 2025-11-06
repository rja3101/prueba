import csv
from pathlib import Path

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

from apps.users.models import Role  # asegúrate de que Role esté ahí

User = get_user_model()


def to_bool(value):
    """
    Convierte '1', '0', 'true', 'false', etc. a bool.
    """
    s = str(value).strip().lower()
    return s in ("1", "true", "t", "yes", "y", "si", "sí")


class Command(BaseCommand):
    help = (
        "Carga docentes desde un CSV con columnas: "
        "username,email,first_name,last_name,role,is_active,is_staff,is_superuser,password"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_path",
            type=str,
            help="Ruta al archivo CSV de docentes (por ejemplo: data/docentes.csv)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])

        if not csv_path.exists():
            self.stderr.write(self.style.ERROR(f"El archivo {csv_path} no existe"))
            return

        created = 0
        updated = 0

        with csv_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                username = row["username"].strip()
                email = row["email"].strip().lower()
                first_name = row["first_name"].strip()
                last_name = row["last_name"].strip()
                role_name = row["role"].strip()

                is_active = to_bool(row.get("is_active", "1"))
                is_staff = to_bool(row.get("is_staff", "0"))
                is_superuser = to_bool(row.get("is_superuser", "0"))
                raw_password = row.get("password", "").strip()

                # Buscar Role (Docente, etc.)
                try:
                    role = Role.objects.get(name=role_name)
                except Role.DoesNotExist:
                    self.stderr.write(
                        self.style.ERROR(
                            f"Role '{role_name}' no existe. Crea ese rol antes o corrige el CSV."
                        )
                    )
                    continue

                user, was_created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        "email": email,
                        "first_name": first_name,
                        "last_name": last_name,
                        "is_active": is_active,
                        "is_staff": is_staff,
                        "is_superuser": is_superuser,
                        "role": role,
                    },
                )

                if was_created:
                    if raw_password:
                        user.set_password(raw_password)
                    else:
                        # por si viene vacío, ponemos algo por defecto
                        user.set_password(username)
                    user.save()
                    created += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"Creado docente: {username} ({email})")
                    )
                else:
                    # Actualizamos datos básicos
                    user.email = email
                    user.first_name = first_name
                    user.last_name = last_name
                    user.is_active = is_active
                    user.is_staff = is_staff
                    user.is_superuser = is_superuser
                    user.role = role

                    # Si quieres resetear la contraseña cuando cambia el CSV, descomenta:
                    # if raw_password:
                    #     user.set_password(raw_password)

                    user.save()
                    updated += 1
                    self.stdout.write(
                        self.style.WARNING(f"Actualizado docente existente: {username}")
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Proceso terminado. Docentes creados: {created}, actualizados: {updated}"
            )
        )
