from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any


@dataclass
class ConversationState:
    # Patient
    patient_name: Optional[str] = None
    patient_age: Optional[int] = None
    patient_phone: Optional[str] = None

    # Appointment intent
    specialty: Optional[str] = None
    doctor_name: Optional[str] = None
    date_iso: Optional[str] = None      # YYYY-MM-DD
    time_24h: Optional[str] = None      # HH:MM

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def is_ready_to_book(self) -> bool:
        return all([
            self.patient_name,
            self.patient_phone,
            self.specialty or self.doctor_name,
            self.doctor_name,   # we will require doctor chosen before booking
            self.date_iso,
            self.time_24h,
        ])
