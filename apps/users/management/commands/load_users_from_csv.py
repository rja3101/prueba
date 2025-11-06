import csv
from pathlib import Path

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()


class Command(BaseCommand):
    help = "Carga usuarios desde un CSV y fuerza username=email y password=cui"

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_path",
            type=str,
            help="Ruta al archivo CSV de usuarios (por ejemplo: data/users.csv)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])

        if not csv_path.exists():
            self.stderr.write(self.style.ERROR(f"El archivo {csv_path} no existe"))
            return

        with csv_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            creados = 0
            actualizados = 0

            for row in reader:
                email = row["email"].strip().lower()
                cui = row["cui"].strip()
                first_name = row.get("first_name", "").strip()
                last_name = row.get("last_name", "").strip()

                # flags del CSV
                is_staff = row.get("is_staff", "False").strip().lower() == "true"
                is_superuser = row.get("is_superuser", "False").strip().lower() == "true"
                is_active = row.get("is_active", "True").strip().lower() == "true"

                # ID de login = email
                username = email

                # Busca por email (clave única típica)
                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        "username": username,
                        "first_name": first_name,
                        "last_name": last_name,
                        "is_staff": is_staff,
                        "is_superuser": is_superuser,
                        "is_active": is_active,
                    },
                )

                if created:
                    # Contraseña inicial = CUI
                    user.set_password(cui)
                    user.save()
                    creados += 1
                    self.stdout.write(self.style.SUCCESS(f"Creado usuario: {email} (CUI: {cui})"))
                else:
                    # Si ya existe, podemos actualizar datos básicos
                    user.username = username
                    user.first_name = first_name
                    user.last_name = last_name
                    user.is_staff = is_staff
                    user.is_superuser = is_superuser
                    user.is_active = is_active

                    # Si quieres **resetear** la contraseña cada vez al CUI, descomenta:
                    # user.set_password(cui)

                    user.save()
                    actualizados += 1
                    self.stdout.write(self.style.WARNING(f"Actualizado usuario existente: {email}"))

            self.stdout.write(self.style.SUCCESS(
                f"Proceso terminado. Creados: {creados}, Actualizados: {actualizados}"
            ))
