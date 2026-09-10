"""Client isolato per l'analisi conversazionale tramite Groq."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv


load_dotenv()

# Modello disponibile per i piani Groq free/developer. Il precedente Llama 3.3
# è stato dismesso per questi piani nell'agosto 2026.
MODEL = "openai/gpt-oss-20b"
DESTINAZIONI_VALIDE = {"FARMACIA", "CASA_COMUNITA", "PRONTO_SOCCORSO"}
CAMPI_ANALISI = (
    "sintomi",
    "durata",
    "intensita",
    "area_interessata",
    "categoria_problema",
    "livello_urgenza",
    "destinazione_consigliata",
    "motivazione",
    "informazioni_mancanti",
)


class GroqServiceError(RuntimeError):
    """Errore sicuro da mostrare nell'interfaccia, senza dettagli sensibili."""


@dataclass(frozen=True)
class GroqResult:
    """Un approfondimento oppure l'analisi strutturata conclusiva."""

    question: str | None = None
    analysis: dict[str, Any] | None = None


def _system_prompt() -> str:
    return """Sei un assistente di orientamento ai servizi sanitari della Regione Lazio.
Non formulare diagnosi, non prescrivere farmaci o terapie e non inventare dati.
Ricevi dati personali minimi e una conversazione su un problema di salute.

Rispondi ESCLUSIVAMENTE con un oggetto JSON valido, senza markdown, con questa struttura:
{
  "azione": "DOMANDA_AGGIUNTIVA" oppure "ANALISI_COMPLETATA",
  "domanda": "stringa o stringa vuota",
  "sintomi": ["stringa"],
  "durata": "stringa",
  "intensita": "stringa",
  "area_interessata": "stringa",
  "categoria_problema": "GENERALE|TRAUMATOLOGICO|PEDIATRICO|OSTETRICO_GINECOLOGICO|ALTRO",
  "livello_urgenza": "stringa",
  "destinazione_consigliata": "FARMACIA|CASA_COMUNITA|PRONTO_SOCCORSO",
  "motivazione": "stringa",
  "informazioni_mancanti": ["stringa"]
}

Se servono chiarimenti e sono ancora disponibili cicli di approfondimento, scegli
DOMANDA_AGGIUNTIVA e poni UNA sola domanda breve e concreta; gli altri campi
possono essere vuoti. Se le informazioni sono sufficienti, scegli ANALISI_COMPLETATA
e compila tutti i campi. Se sono presenti possibili segnali di emergenza, orienta al
PRONTO_SOCCORSO, spiegando in modo prudente che si tratta di orientamento e non di diagnosi.
"""


class GroqService:
    """Adapter del SDK Groq, senza dipendenze da Streamlit."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model or os.getenv("GROQ_MODEL", MODEL)

    def assess(
        self,
        *,
        profile: dict[str, Any],
        conversation: list[dict[str, str]],
        follow_up_count: int,
    ) -> GroqResult:
        if not self.api_key:
            raise GroqServiceError(
                "Configurazione mancante: imposta la variabile d'ambiente GROQ_API_KEY."
            )

        try:
            from groq import Groq
        except ImportError as error:
            raise GroqServiceError("Il pacchetto Groq non è installato nell'ambiente.") from error

        payload = {
            "dati_personali": profile,
            "conversazione": conversation,
            "cicli_approfondimento_gia_usati": follow_up_count,
            "massimo_cicli_approfondimento": 3,
            "richiedi_analisi_finale": follow_up_count >= 3,
        }
        try:
            response = Groq(api_key=self.api_key).chat.completions.create(
                model=self.model,
                temperature=0.1,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": _system_prompt()},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
            )
            content = response.choices[0].message.content or "{}"
            data = json.loads(content)
        except json.JSONDecodeError as error:
            raise GroqServiceError("Groq ha restituito un formato non valido. Riprova.") from error
        except Exception as error:
            raise GroqServiceError(self._friendly_error(error)) from error

        return self._validate(data, force_final=follow_up_count >= 3)

    @staticmethod
    def _validate(data: Any, *, force_final: bool) -> GroqResult:
        if not isinstance(data, dict):
            raise GroqServiceError("Groq ha restituito una risposta non utilizzabile. Riprova.")

        action = data.get("azione")
        if action == "DOMANDA_AGGIUNTIVA" and not force_final:
            question = data.get("domanda")
            if isinstance(question, str) and question.strip():
                return GroqResult(question=question.strip())
            raise GroqServiceError("Groq non ha formulato una domanda valida. Riprova.")

        if action != "ANALISI_COMPLETATA":
            raise GroqServiceError("Groq non ha restituito un'analisi valida. Riprova.")
        missing = [field for field in CAMPI_ANALISI if field not in data]
        if missing or data.get("destinazione_consigliata") not in DESTINAZIONI_VALIDE:
            raise GroqServiceError("L'analisi ricevuta da Groq è incompleta. Riprova.")
        return GroqResult(analysis={field: data[field] for field in CAMPI_ANALISI})

    @staticmethod
    def _friendly_error(error: Exception) -> str:
        """Traduce gli errori dell'SDK senza esporre chiavi o dettagli interni."""
        status_code = getattr(error, "status_code", None)
        if status_code == 401:
            return "La chiave GROQ_API_KEY non è valida o non è più attiva."
        if status_code == 403:
            return "Questa chiave non è autorizzata a usare il modello configurato."
        if status_code == 404:
            return "Il modello Groq configurato non è disponibile per questo account."
        if status_code == 429:
            return "È stato raggiunto il limite di richieste Groq. Attendi e riprova."

        cause = str(error.__cause__ or error).casefold()
        dns_markers = ("nodename", "getaddrinfo", "name or service not known", "dns")
        if any(marker in cause for marker in dns_markers):
            return (
                "Impossibile raggiungere Groq: il DNS non risolve api.groq.com. "
                "Verifica la connessione internet o la configurazione DNS del computer."
            )
        return "Non è stato possibile raggiungere Groq. Verifica rete e chiave API, poi riprova."
