# apps/academics/schedule_data.py
import csv
from pathlib import Path
from django.conf import settings

def normalize_day(day: str) -> str:
    if not day:
        return ""
    d = str(day).strip()
    # normaliza tildes comunes
    d = d.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    d = d.replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U")
    d = d.capitalize()
    # Miércoles -> Miercoles (como en tus templates)
    if d.lower() == "miercoles":
        return "Miercoles"
    return d

def normalize_time(t) -> str:
    """
    Acepta '08:50:00', '08:50' o time/datetime -> retorna '08:50'
    """
    if t is None:
        return ""
    s = str(t).strip()
    # si viene HH:MM:SS
    if len(s) >= 5 and ":" in s:
        parts = s.split(":")
        return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}"
    return s

def load_horarios_from_csv(csv_path: Path) -> dict:
    horarios = {}
    if not csv_path.exists():
        return horarios

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Ajusta a tus columnas reales (según tu CSV)
            course_code = str(row.get("course_code", "")).strip()
            section = str(row.get("section", "")).strip().upper()
            day = normalize_day(row.get("day_of_the_week", ""))
            start = normalize_time(row.get("start_time", ""))
            end = normalize_time(row.get("end_time", ""))
            classroom = str(row.get("classroom", "")).strip()

            if not course_code or not section or not day or not start or not end:
                continue

            key = (course_code, section)
            horarios.setdefault(key, []).append(
                {"day": day, "start": start, "end": end, "classroom": classroom}
            )

    # ordena por día/hora para que se vea bonito
    def day_order(d):
        order = {"Lunes": 1, "Martes": 2, "Miercoles": 3, "Jueves": 4, "Viernes": 5}
        return order.get(d, 99)

    for key in horarios:
        horarios[key].sort(key=lambda x: (day_order(x["day"]), x["start"]))

    return horarios


CSV_PATH = Path(settings.BASE_DIR) / "data" / "horarios.csv"
HORARIOS = load_horarios_from_csv(CSV_PATH)
