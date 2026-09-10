"""Ricerca e ordinamento dei Pronto Soccorso dal dataset locale del Lazio."""

from __future__ import annotations

import csv
from dataclasses import dataclass, replace
from pathlib import Path

from case_comunita import haversine_km


DATASET_PATH = Path(__file__).parent / "data" / "Pronto_Soccorso_Lazio_Coordinate.csv"

SORT_OPTIONS = {
    "Distanza": "distance_km",
    "Totale pazienti in attesa": "total_waiting",
    "Codici rossi in attesa": "red_waiting",
    "Codici gialli in attesa": "yellow_waiting",
    "Codici verdi in attesa": "green_waiting",
    "Codici bianchi in attesa": "white_waiting",
}


@dataclass(frozen=True)
class ProntoSoccorso:
    code: str
    name: str
    emergency_type: str
    comune: str
    asl: str
    address: str
    latitude: float
    longitude: float
    updated_at: str
    red_waiting: int
    yellow_waiting: int
    green_waiting: int
    white_waiting: int
    unassigned_waiting: int
    total_waiting: int
    total_treatment: int
    total_observation: int
    total_present: int
    distance_km: float = 0.0


def _as_int(value: str | None) -> int:
    try:
        return int(value or 0)
    except ValueError:
        return 0


def load_pronto_soccorso(path: Path = DATASET_PATH) -> list[ProntoSoccorso]:
    """Legge esclusivamente il dataset locale con coordinate dei Pronto Soccorso."""
    if not path.exists():
        raise FileNotFoundError("Dataset dei Pronto Soccorso non trovato.")

    hospitals: list[ProntoSoccorso] = []
    with path.open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source, delimiter=";"):
            try:
                latitude = float((row.get("LATITUDINE") or "").replace(",", "."))
                longitude = float((row.get("LONGITUDINE") or "").replace(",", "."))
                if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                    continue
                hospitals.append(
                    ProntoSoccorso(
                        code=(row.get("CODICE") or "").strip(),
                        name=(row.get("ISTITUTO") or "").strip(),
                        emergency_type=(row.get("TIPO") or "").strip(),
                        comune=(row.get("COMUNE") or "").strip(),
                        asl=(row.get("ASL") or "").strip(),
                        address=(row.get("INDIRIZZO") or "").strip(),
                        latitude=latitude,
                        longitude=longitude,
                        updated_at=(row.get("DATA") or "").strip(),
                        red_waiting=_as_int(row.get("ROSSI_ATT")),
                        yellow_waiting=_as_int(row.get("GIALLI_ATT")),
                        green_waiting=_as_int(row.get("VERDI_ATT")),
                        white_waiting=_as_int(row.get("BIANCHI_ATT")),
                        unassigned_waiting=_as_int(row.get("NONESEG_ATT")),
                        total_waiting=_as_int(row.get("TOT_ATT")),
                        total_treatment=_as_int(row.get("TOT_TRATT")),
                        total_observation=_as_int(row.get("TOT_OB")),
                        total_present=_as_int(row.get("TUTTI")),
                    )
                )
            except (TypeError, ValueError):
                continue
    return hospitals


def nearest_pronto_soccorso(latitude: float, longitude: float, limit: int = 5) -> list[ProntoSoccorso]:
    """Seleziona i cinque PS candidati più vicini, prima di applicare un ordinamento."""
    ranked = [
        replace(
            hospital,
            distance_km=haversine_km(latitude, longitude, hospital.latitude, hospital.longitude),
        )
        for hospital in load_pronto_soccorso()
    ]
    return sorted(ranked, key=lambda hospital: hospital.distance_km)[:limit]


def sort_candidates(candidates: list[ProntoSoccorso], criterion: str) -> list[ProntoSoccorso]:
    """Ordina solamente i cinque candidati, come previsto dai requisiti MVP."""
    field = SORT_OPTIONS.get(criterion, "distance_km")
    return sorted(candidates, key=lambda hospital: getattr(hospital, field))
