from __future__ import annotations

import csv
from datetime import datetime, date
from typing import Dict, List, Any
from zoneinfo import ZoneInfo
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DOCTORS_FILE = DATA_DIR / "doctors.csv"
SCHEDULES_FILE = DATA_DIR / "schedules.csv"
APPOINTMENTS_FILE = DATA_DIR / "appointments.csv"

IST = ZoneInfo("Asia/Kolkata")

WEEKDAY_MAP = {
    "Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3,
    "Fri": 4, "Sat": 5, "Sun": 6,
}


# -------------------------
# Loaders
# -------------------------

def load_doctors() -> List[Dict[str, str]]:
    with DOCTORS_FILE.open() as f:
        return list(csv.DictReader(f))


def load_schedules() -> Dict[str, Dict[str, Any]]:
    schedules = {}
    with SCHEDULES_FILE.open() as f:
        for row in csv.DictReader(f):
            schedules[row["doctor_name"]] = {
                "working_days": [WEEKDAY_MAP[d] for d in row["working_days"].split()],
                "slots": row["slots"].split("|"),
            }
    return schedules


def load_appointments() -> List[Dict[str, str]]:
    if not APPOINTMENTS_FILE.exists():
        return []
    with APPOINTMENTS_FILE.open() as f:
        return list(csv.DictReader(f))


def save_appointment(record: Dict[str, str]) -> None:
    exists = APPOINTMENTS_FILE.exists()
    with APPOINTMENTS_FILE.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=record.keys())
        if not exists:
            writer.writeheader()
        writer.writerow(record)


# -------------------------
# Tool APIs
# -------------------------

def list_specialties() -> List[str]:
    doctors = load_doctors()
    return sorted({d["specialty"] for d in doctors})


def find_doctors(specialty: str) -> List[Dict[str, str]]:
    doctors = load_doctors()
    s = specialty.lower()
    return [d for d in doctors if d["specialty"].lower() == s]


def get_availability(doctor_name: str, date_iso: str) -> List[str]:
    schedules = load_schedules()
    appointments = load_appointments()

    if doctor_name not in schedules:
        return []

    d = datetime.fromisoformat(date_iso).date()
    weekday = d.weekday()

    rule = schedules[doctor_name]
    if weekday not in rule["working_days"]:
        return []

    booked = {
        a["time_24h"]
        for a in appointments
        if a["doctor_name"] == doctor_name and a["date_iso"] == date_iso
    }

    return [s for s in rule["slots"] if s not in booked]


def book_appointment(
    doctor_name: str,
    date_iso: str,
    time_24h: str,
    patient: Dict[str, str],
) -> Dict[str, Any]:

    available = get_availability(doctor_name, date_iso)
    if time_24h not in available:
        return {
            "status": "failed",
            "reason": "slot_not_available",
        }

    appt_id = f"APT-{int(datetime.now().timestamp())}"

    record = {
        "appointment_id": appt_id,
        "doctor_name": doctor_name,
        "date_iso": date_iso,
        "time_24h": time_24h,
        "patient_name": patient["name"],
        "patient_phone": patient["phone"],
        "created_at": datetime.now(IST).isoformat(timespec="seconds"),
    }

    save_appointment(record)

    return {
        "status": "confirmed",
        "appointment": record,
    }


def get_current_datetime(timezone: str = "Asia/Kolkata") -> dict:
    tz = ZoneInfo(timezone)
    now = datetime.now(tz)
    return {
        "timezone": timezone,
        "iso_datetime": now.isoformat(timespec="seconds"),
        "date_iso": now.date().isoformat(),
        "weekday": now.strftime("%A"),
    }
