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

1. L'utente inserisce dati essenziali e posizione.
2. Descrive il problema nella chat.
3. Groq può chiedere fino a tre chiarimenti, uno alla volta.
4. Groq restituisce JSON validato con l'orientamento consigliato.
