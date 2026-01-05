from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Any, Optional

APPOINTMENTS: List[Dict[str, Any]] = []


@dataclass(frozen=True)
class Doctor:
    name: str
    specialty: str


# In-memory "DB"
DOCTORS: List[Doctor] = [
    Doctor(name="Dr X", specialty="Orthopedics"),
    Doctor(name="Dr Y", specialty="Orthopedics"),
    Doctor(name="Dr A", specialty="General Medicine"),
]

# availability keyed by (doctor_name, date_iso) -> list of times
AVAILABILITY: Dict[str, List[str]] = {
    "Dr X|2025-12-23": ["10:00", "11:00"],
    "Dr X|2025-12-24": ["10:30", "11:30"],
    "Dr Y|2025-12-23": ["11:00", "12:00"],
}


def find_doctors(specialty: str) -> List[Dict[str, str]]:
    """Return doctors matching the given specialty (case-insensitive)."""
    s = specialty.strip().lower()
    return [{"name": d.name, "specialty": d.specialty} for d in DOCTORS if d.specialty.lower() == s]


def get_availability(doctor_name: str, date_iso: str) -> List[str]:
    """Return available time slots for a doctor on a given date (YYYY-MM-DD)."""
    key = f"{doctor_name}|{date_iso}"
    return AVAILABILITY.get(key, [])

APPOINTMENTS: List[Dict[str, Any]] = []


def book_appointment(
    doctor_name: str,
    date_iso: str,
    time_24h: str,
    patient: Dict[str, str],
) -> Dict[str, Any]:
    """
    Book an appointment by removing the slot and storing appointment details.
    Returns confirmation or error.
    """
    key = f"{doctor_name}|{date_iso}"
    slots = AVAILABILITY.get(key, [])

    if time_24h not in slots:
        return {"status": "failed", "reason": "slot_not_available", "doctor": doctor_name, "date": date_iso, "time": time_24h}

    # remove the slot (mark unavailable)
    slots.remove(time_24h)
    AVAILABILITY[key] = slots

    appt_id = f"APT-{len(APPOINTMENTS) + 1:04d}"
    record = {
        "id": appt_id,
        "doctor": doctor_name,
        "date": date_iso,
        "time": time_24h,
        "patient": patient,
    }
    APPOINTMENTS.append(record)

    return {"status": "confirmed", "appointment": record}
