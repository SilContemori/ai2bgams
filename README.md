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

## Farmacie

Quando Groq consiglia `FARMACIA`, l'app legge `data/farmaciereglaziolatlon.csv`,
esclude le righe con validità terminata e mostra le cinque farmacie aperte più
vicine. Il file non contiene orari né turni: per il prototipo gli orari sono
simulati in modo deterministico (08:00–20:00, alcune chiuse nel weekend o la
domenica, alcune H24) e sono sempre contrassegnati come simulati nell'interfaccia.

## Pronto Soccorso

Quando Groq consiglia `PRONTO_SOCCORSO`, l'app usa esclusivamente
`data/Pronto_Soccorso_Lazio_Coordinate.csv`, seleziona i cinque PS più vicini e
consente di ordinarli per distanza, attese totali o codice di triage. Per ogni
struttura mostra persone presenti (`TUTTI`), attese, trattamento e osservazione.
Il dataset non contiene la capacità o i posti disponibili, che vengono quindi
esplicitamente indicati come non disponibili.
