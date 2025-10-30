# SISACAD Django (Starter)

Proyecto base modular para un **Sistema Académico** en Django + MariaDB, dividido en 3 apps:
- `apps/users` — autenticación y roles
- `apps/academics` — cursos, matrículas, notas, contenidos
- `apps/attendance` — horarios, sesiones, asistencia (con IP)

## Requisitos
- Python 3.10+
- MariaDB 11+
- (Windows) Paquete compilación si usas `mysqlclient`

## Configuración rápida
```bash
# 1) Clonar y entrar
# git clone <repo> && cd sisacad-django

# 2) Entorno virtual
python -m venv .venv
. .venv/Scripts/activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 3) Dependencias
pip install -r requirements.txt

# 4) Variables de entorno
copy .env.example .env  # Windows
# cp .env.example .env   # Linux/Mac

# 5) Migraciones y superusuario
set DJANGO_SETTINGS_MODULE=sisacad.settings.dev  # Windows CMD
# export DJANGO_SETTINGS_MODULE=sisacad.settings.dev  # Linux/Mac
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser

# 6) Correr
python manage.py runserver
```

## Base de datos MariaDB (ejemplo)
```sql
CREATE DATABASE sisacad CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
CREATE USER 'sisacad_user'@'localhost' IDENTIFIED BY 'tu_contraseña_segura';
GRANT ALL PRIVILEGES ON sisacad.* TO 'sisacad_user'@'localhost';
FLUSH PRIVILEGES;
```

## Estructura
```
sisacad-django/
├── manage.py
├── requirements.txt
├── .env.example
├── sisacad/
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── apps/
│   ├── users/
│   ├── academics/
│   └── attendance/
└── templates/
    ├── base.html
    └── home.html
```

## Ramas sugeridas (Git)
- `main` — estable
- `dev-users`, `dev-academics`, `dev-attendance` — trabajo por integrante

## Notas
- El proyecto ya está listo para **roles** y **separación por módulos**.
- Puedes agregar `django-import-export` en admin para subir Excel de estudiantes y notas.
