# Orientamento ai servizi sanitari

Applicazione Streamlit per raccogliere una problematica e orientare l'utente verso
Farmacia, Casa della Comunità o Pronto Soccorso. Il risultato è informativo e non
costituisce diagnosi o prescrizione.

## Avvio locale

```bash
uv sync
cp .env.example .env
# inserisci la chiave nell'unica variabile GROQ_API_KEY del file .env
uv run streamlit run main.py
```

La chiave non viene salvata nel codice. Il file `.env` è escluso dal repository.
Il modello predefinito è `openai/gpt-oss-20b`; può essere cambiato tramite
`GROQ_MODEL` nel file `.env`.

## Flusso attuale

1. L'utente inserisce dati essenziali e posizione completa (via, civico, CAP, comune e provincia).
2. Descrive il problema nella chat.
3. Groq può chiedere fino a tre chiarimenti, uno alla volta.
4. Groq restituisce JSON validato con l'orientamento consigliato.

## Case della Comunità

Quando Groq consiglia `CASA_COMUNITA`, l'app legge
`data/Case_della_Comunita_Lazio.csv`, geocodifica l'indirizzo dell'utente e mostra
al massimo cinque strutture ordinate per distanza. Nel weekend e nei festivi
esclude le sedi non indicate come aperte dal dataset.

Il CSV ricevuto riporta l'apertura nei weekend/festivi ma non le fasce orarie
giornaliere: nei feriali la disponibilità viene quindi indicata come “da
verificare” e l'app offre il collegamento alla scheda ufficiale con gli orari.
