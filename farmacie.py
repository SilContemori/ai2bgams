"""Ricerca delle farmacie attive nel dataset regionale locale."""

from __future__ import annotations

import csv
from dataclasses import dataclass, replace
from datetime import date, datetime
from pathlib import Path

from case_comunita import haversine_km


DATASET_PATH = Path(__file__).parent / "data" / "farmaciereglaziolatlon.csv"


@dataclass(frozen=True)
class Farmacia:
    pharmacy_id: int
    name: str
    address: str
    cap: str
    comune: str
    provincia: str
    typology: str
    latitude: float
    longitude: float
    valid_until: date | None
    distance_km: float = 0.0

    @property
    def full_address(self) -> str:
        cap = self.cap.zfill(5) if self.cap.isdigit() else self.cap
        return f"{self.address}, {cap} {self.comune} ({self.provincia})"

    @property
    def simulated_schedule(self) -> str:
        """Orario fittizio stabile, usato solo finché non esiste una fonte ufficiale."""
        if self.pharmacy_id % 17 == 0:
            return "Aperta 24 ore su 24"
        if self.pharmacy_id % 5 == 0:
            return "Lun–Ven 08:00–20:00 · Sab e Dom chiusa"
        if self.pharmacy_id % 3 == 0:
            return "Lun–Sab 08:00–20:00 · Dom chiusa"
        return "Tutti i giorni 08:00–20:00"

    def is_open_now(self, now: datetime | None = None) -> bool:
        current = now or datetime.now()
        if self.pharmacy_id % 17 == 0:
            return True
        if not 8 <= current.hour < 20:
            return False
        if self.pharmacy_id % 5 == 0:
            return current.weekday() < 5
        if self.pharmacy_id % 3 == 0:
            return current.weekday() < 6
        return True


def _parse_date(value: str | None) -> date | None:
    raw = (value or "").strip()
    if not raw or raw == "-":
        return None
    return datetime.strptime(raw, "%d/%m/%Y").date()


def _active_on(row: dict[str, str], today: date) -> bool:
    try:
        start = _parse_date(row.get("DATAINIZIOVALIDITA"))
        end = _parse_date(row.get("DATAFINEVALIDITA"))
    except ValueError:
        return False
    return (start is None or start <= today) and (end is None or end >= today)


def load_active_farmacie(path: Path = DATASET_PATH, today: date | None = None) -> list[Farmacia]:
    """Legge solo le farmacie con validità attuale e coordinate utilizzabili."""
    if not path.exists():
        raise FileNotFoundError("Dataset delle farmacie non trovato.")

    reference_date = today or date.today()
    pharmacies: list[Farmacia] = []
    with path.open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source, delimiter=";"):
            if not _active_on(row, reference_date):
                continue
            try:
                latitude = float((row.get("LATITUDINE") or "").replace(",", "."))
                longitude = float((row.get("LONGITUDINE") or "").replace(",", "."))
                pharmacies.append(
                    Farmacia(
                        pharmacy_id=int(row["CODICEIDENTIFICATIVOFARMACIA"]),
                        name=(row.get("DESCRIZIONEFARMACIA") or "").strip(),
                        address=(row.get("INDIRIZZO") or "").strip(),
                        cap=(row.get("CAP") or "").strip(),
                        comune=(row.get("DESCRIZIONECOMUNE") or "").strip().title(),
                        provincia=(row.get("SIGLAPROVINCIA") or "").strip().upper(),
                        typology=(row.get("DESCRIZIONETIPOLOGIA") or "").strip(),
                        latitude=latitude,
                        longitude=longitude,
                        valid_until=_parse_date(row.get("DATAFINEVALIDITA")),
                    )
                )
            except (TypeError, ValueError):
                continue
    return pharmacies


def nearest_active_farmacie(latitude: float, longitude: float, limit: int = 5) -> list[Farmacia]:
    """Restituisce al massimo cinque farmacie attive, ordinate per distanza."""
    ranked = [
        replace(
            pharmacy,
            distance_km=haversine_km(latitude, longitude, pharmacy.latitude, pharmacy.longitude),
        )
        for pharmacy in load_active_farmacie()
    ]
    return sorted(ranked, key=lambda pharmacy: pharmacy.distance_km)[:limit]


def nearest_open_farmacie(
    latitude: float, longitude: float, now: datetime | None = None, limit: int = 5
) -> list[Farmacia]:
    """Restituisce le farmacie attive e aperte secondo l'orario simulato del prototipo."""
    current = now or datetime.now()
    ranked = [
        replace(
            pharmacy,
            distance_km=haversine_km(latitude, longitude, pharmacy.latitude, pharmacy.longitude),
        )
        for pharmacy in load_active_farmacie(today=current.date())
        if pharmacy.is_open_now(current)
    ]
    return sorted(ranked, key=lambda pharmacy: pharmacy.distance_km)[:limit]
