"""Ricerca delle Case della Comunità dal dataset locale della Regione Lazio."""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


DATASET_PATH = Path(__file__).parent / "data" / "Case_della_Comunita_Lazio.csv"


class LocationError(RuntimeError):
    """La posizione dell'utente non può essere convertita in coordinate."""


@dataclass(frozen=True)
class CasaComunita:
    name: str
    address: str
    comune: str
    asl: str
    phone: str
    weekend_open: bool
    latitude: float
    longitude: float
    official_url: str
    distance_km: float = 0.0

    def availability(self, now: datetime | None = None) -> tuple[bool, str]:
        """Indica la disponibilità nota dal dataset, senza inventare fasce orarie."""
        today = now or datetime.now()
        if today.weekday() < 5:
            return True, "Orari feriali non presenti nel dataset: verifica prima di recarti"
        if self.weekend_open:
            return True, "Indicata come aperta nel weekend/festivi: verifica l'orario"
        return False, "Non indicata come aperta nel weekend/festivi"


def _to_float(value: str | None) -> float:
    return float((value or "").strip().replace(",", "."))


def load_case_comunita(path: Path = DATASET_PATH) -> list[CasaComunita]:
    if not path.exists():
        raise FileNotFoundError("Dataset delle Case della Comunità non trovato.")

    structures: list[CasaComunita] = []
    with path.open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source, delimiter=";"):
            try:
                structures.append(
                    CasaComunita(
                        name=row["Denominazione"].strip(),
                        address=row["Indirizzo"].strip(),
                        comune=row["Comune"].strip(),
                        asl=row["ASL"].strip(),
                        phone=(row.get("Telefono") or "").strip(),
                        weekend_open=(row.get("Aperta_Weekend_Festivi") or "").strip().casefold()
                        in {"si", "sì", "yes"},
                        latitude=_to_float(row.get("Latitudine")),
                        longitude=_to_float(row.get("Longitudine")),
                        official_url=(row.get("Link_PDF_Ufficiale") or "").strip(),
                    )
                )
            except (KeyError, ValueError):
                # Una riga difettosa non deve impedire la ricerca delle altre strutture.
                continue
    return structures


def haversine_km(lat_a: float, lon_a: float, lat_b: float, lon_b: float) -> float:
    earth_radius_km = 6371.0088
    lat_delta = math.radians(lat_b - lat_a)
    lon_delta = math.radians(lon_b - lon_a)
    value = (
        math.sin(lat_delta / 2) ** 2
        + math.cos(math.radians(lat_a))
        * math.cos(math.radians(lat_b))
        * math.sin(lon_delta / 2) ** 2
    )
    return earth_radius_km * 2 * math.asin(math.sqrt(value))


def nearest_available_case_comunita(
    latitude: float, longitude: float, now: datetime | None = None, limit: int = 5
) -> list[CasaComunita]:
    """Restituisce massimo cinque strutture, escludendo quelle chiuse nel weekend."""
    ranked: list[CasaComunita] = []
    for structure in load_case_comunita():
        available, _ = structure.availability(now)
        if available:
            ranked.append(
                CasaComunita(
                    **{**structure.__dict__, "distance_km": haversine_km(
                        latitude, longitude, structure.latitude, structure.longitude
                    )}
                )
            )
    return sorted(ranked, key=lambda item: item.distance_km)[:limit]


def geocode_address(address: str) -> tuple[float, float]:
    """Geocodifica un indirizzo tramite Nominatim, esclusivamente quando necessario."""
    import json
    from urllib.error import URLError
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

    query = urlencode({"q": address, "format": "jsonv2", "limit": 1})
    request = Request(
        f"https://nominatim.openstreetmap.org/search?{query}",
        headers={"User-Agent": "orientamento-sanitario-lazio/0.1"},
    )
    try:
        with urlopen(request, timeout=10) as response:  # noqa: S310 - URL fisso e attendibile
            results = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, OSError) as error:
        raise LocationError("Non è stato possibile contattare il servizio di geocodifica.") from error
    if not results:
        raise LocationError("Indirizzo non trovato: controlla e riprova.")
    try:
        return float(results[0]["lat"]), float(results[0]["lon"])
    except (IndexError, KeyError, TypeError, ValueError) as error:
        raise LocationError("Il servizio di geocodifica ha restituito dati non validi.") from error
