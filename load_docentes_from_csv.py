import csv
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from apps.users.models import Role

User = get_user_model()


def run():
    # Ruta al CSV
    csv_path = Path(settings.BASE_DIR) / "data" / "docentes (1).csv"
    print("Leyendo CSV:", csv_path)

    if not csv_path.exists():
        print("ERROR: No existe el archivo:", csv_path)
        return

    created_count = 0
    updated_count = 0

    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            username = (row.get("username") or "").strip()
            email = (row.get("email") or "").strip()
            first_name = (row.get("first_name") or "").strip()
            last_name = (row.get("last_name") or "").strip()
            role_name = (row.get("role") or "").strip()
            is_active = (row.get("is_active") or "1").strip() == "1"
            is_staff = (row.get("is_staff") or "0").strip() == "1"
            is_superuser = (row.get("is_superuser") or "0").strip() == "1"
            raw_password = (row.get("password") or "").strip()

            if not username:
                print("[WARN] Fila sin username, la salto:", row)
                continue

            # Rol (Docente, Alumno, etc.)
            role = None
            if role_name:
                role, _ = Role.objects.get_or_create(name=role_name)

            user, created = User.objects.get_or_create(username=username)

            user.email = email
            user.first_name = first_name
            user.last_name = last_name
            user.is_active = is_active
            user.is_staff = is_staff
            user.is_superuser = is_superuser

            if role is not None:
                user.role = role

            # Solo seteamos password si viene algo en el CSV
            if raw_password:
                user.set_password(raw_password)

            user.save()

            if created:
                created_count += 1
                print(f"[CREADO] {username} ({email})")
            else:
                updated_count += 1
                print(f"[ACTUALIZADO] {username} ({email})")

    print("==== RESUMEN ====")
    print("Usuarios creados:", created_count)
    print("Usuarios actualizados:", updated_count)


# Para que se ejecute al usar `python manage.py shell < load_docentes_from_csv.py`
if __name__ == "__main__":
    run()
