# Documento dei Requisiti Funzionali

## Piattaforma Web di Orientamento ai Servizi Sanitari

### 1. Obiettivo

Realizzare un prototipo web semplice che aiuti l'utente a individuare la struttura sanitaria più appropriata in funzione:

* delle informazioni personali inserite;
* della problematica descritta;
* della posizione dell'utente;
* della classificazione effettuata tramite LLM;
* della distanza dalle strutture disponibili;
* della situazione in tempo reale dei Pronto Soccorso della Regione Lazio.

La piattaforma ha finalità esclusivamente informative e di supporto all'orientamento e **non effettua diagnosi mediche**.

La soluzione deve essere sviluppata privilegiando semplicità, velocità di implementazione e leggibilità del codice.

---

# 2. Architettura generale

Per l'MVP si prevede:

* **Frontend:** Streamlit;
* **Backend:** Python, integrato direttamente nell'applicazione Streamlit;
* **LLM:** Groq tramite API;
* **Geocodifica:** servizio esterno per trasformare l'indirizzo in coordinate geografiche;
* **Calcolo distanze:** effettuato localmente tramite coordinate geografiche;
* **Dati PS:** API/Open Data Regione Lazio;
* **Farmacie:** dataset Open Data Regione Lazio;
* **Case della Comunità:** dataset locale CSV predisposto a partire dalle fonti ufficiali regionali/ASL;
* nessun sistema di autenticazione;
* nessun database obbligatorio;
* nessuna persistenza dei dati personali dell'utente.

L'applicazione può essere organizzata prevalentemente come **interfaccia conversazionale/chat**.

---

# 3. Flusso principale

Il flusso utente deve essere il seguente:

**Inserimento dati → Descrizione problema → Eventuali domande LLM → Classificazione → Individuazione strutture → Visualizzazione risultati**

L'utente avvia una nuova conversazione e inserisce le informazioni richieste.

Il sistema raccoglie le informazioni, eventualmente pone domande aggiuntive e successivamente classifica il bisogno indirizzandolo verso una delle tre categorie:

1. **Farmacia**
2. **Casa della Comunità**
3. **Pronto Soccorso**

---

# 4. Requisiti funzionali

## RF-01 – Raccolta dati dell'utente

Il sistema deve permettere all'utente di inserire almeno:

* età;
* sesso;
* peso;
* altezza;
* indirizzo o posizione testuale;
* eventuali ulteriori informazioni personali ritenute utili.

Nome, cognome, codice fiscale e altri identificativi reali non sono necessari per il prototipo.

L'indirizzo deve essere utilizzato esclusivamente per determinare la posizione geografica dell'utente.

---

## RF-02 – Inserimento della problematica

Il sistema deve presentare all'utente un campo libero in cui descrivere la propria problematica.

L'interfaccia deve invitare esplicitamente l'utente a fornire una descrizione dettagliata, ad esempio indicando:

* sintomi;
* area del corpo interessata;
* intensità;
* durata;
* modalità di comparsa;
* eventuali sintomi associati.

Esempio:

> "Descrivi nel modo più dettagliato possibile il problema che stai riscontrando e da quanto tempo è presente."

---

## RF-03 – Raccolta dinamica di informazioni

Dopo la prima descrizione, l'LLM può identificare informazioni mancanti necessarie alla classificazione.

Il sistema deve quindi poter porre alcune domande aggiuntive all'utente.

Esempio:

Utente:

> "Ho molto mal di gola."

Assistente:

> "Da quanto tempo hai questo dolore? Hai febbre? Hai difficoltà a respirare o deglutire?"

Per mantenere semplice il prototipo, il numero di interazioni aggiuntive dovrebbe essere limitato indicativamente a **massimo 2-3 cicli di domande**.

---

## RF-04 – Analisi tramite Groq

Le informazioni raccolte devono essere inviate tramite API a un modello disponibile attraverso Groq.

Il modello deve trasformare la conversazione in una rappresentazione strutturata.

L'output dell'LLM deve essere JSON e contenere almeno:

```json
{
  "sintomi": [],
  "durata": "",
  "intensita": "",
  "area_interessata": "",
  "categoria_problema": "",
  "livello_urgenza": "",
  "destinazione_consigliata": "",
  "motivazione": "",
  "informazioni_mancanti": []
}
```

`destinazione_consigliata` deve assumere esclusivamente uno dei seguenti valori:

```text
FARMACIA
CASA_COMUNITA
PRONTO_SOCCORSO
```

L'LLM non deve formulare una diagnosi né prescrivere terapie.

---

## RF-05 – Geocodifica della posizione

L'indirizzo inserito dall'utente deve essere convertito in:

```text
latitudine
longitudine
```

Per il prototipo può essere utilizzato un servizio basato su OpenStreetMap/Nominatim, ad esempio tramite la libreria Python `geopy`.

Esempio:

```text
Via Ostiense 159, Roma
        ↓
41.86..., 12.47...
```

Le coordinate saranno utilizzate per calcolare la distanza dalle strutture.

---

# 5. Flusso Farmacia

## RF-06 – Individuazione delle farmacie

Se l'LLM restituisce:

```text
FARMACIA
```

il sistema deve:

1. recuperare l'elenco delle farmacie;
2. ottenere/utilizzare le coordinate delle farmacie;
3. calcolare la distanza dalla posizione dell'utente;
4. ordinare le farmacie dalla più vicina alla più lontana;
5. visualizzare al massimo le **5 farmacie più vicine**.

Per ciascuna farmacia devono essere visualizzati almeno:

* nome;
* indirizzo;
* distanza dall'utente.

Come sorgente può essere utilizzato il dataset **Farmacie della Regione Lazio**, che contiene dati anagrafici e di localizzazione delle farmacie.

---

# 6. Flusso Casa della Comunità

## RF-07 – Individuazione delle Case della Comunità

Se l'LLM restituisce:

```text
CASA_COMUNITA
```

il sistema deve individuare le Case della Comunità più vicine.

Per l'MVP non è necessario costruire una complessa integrazione real-time.

La soluzione consigliata consiste nel predisporre un file:

```text
case_comunita.csv
```

contenente almeno:

```text
nome
indirizzo
comune
asl
latitudine
longitudine
telefono
orari
```

Le informazioni possono essere inizialmente raccolte dalle pagine ufficiali della Regione Lazio e delle ASL. Il portale regionale CuraLazio mantiene una sezione dedicata alle Case della Comunità, mentre le singole ASL pubblicano indirizzi e informazioni sulle strutture.

Le coordinate possono essere calcolate **una volta sola** partendo dagli indirizzi tramite geocodifica e salvate nel CSV.

Questo evita di geocodificare tutte le strutture a ogni richiesta.

Quando viene effettuata una ricerca, il sistema deve:

1. leggere `case_comunita.csv`;
2. calcolare la distanza rispetto all'utente;
3. ordinare le strutture;
4. mostrare al massimo le **5 più vicine**.

Per ciascuna devono essere visualizzati:

* nome;
* indirizzo;
* distanza;
* eventuale telefono;
* eventuale orario.

### Guardia medica

Quando viene consigliata una Casa della Comunità o una Farmacia, deve inoltre essere mostrata una sezione:

**"Hai bisogno di assistenza medica?"**

con possibilità di contattare il servizio di continuità assistenziale.

Per il Lazio può essere mostrato il numero:

**116117**

Il portale Salute Lazio indica il 116117 come numero per la centrale di ascolto della continuità assistenziale regionale.

---

# 7. Flusso Pronto Soccorso

## RF-08 – Recupero dati PS in tempo reale

Se l'LLM restituisce:

```text
PRONTO_SOCCORSO
```

il sistema deve recuperare i dati in tempo reale dal dataset Open Data Lazio:

**"Pronto Soccorso – Accessi in tempo reale".**

Il portale Open Data Lazio mette a disposizione API REST basate su CKAN e consente la consultazione dei dati senza scaricare necessariamente l'intero dataset.

Il resource ID da utilizzare è:

```text
12c31624-f1a4-4874-a903-8954549ddb81
```

Tra i campi disponibili risultano:

```text
ISTITUTO
TIPO
COMUNE
ASL
DATA

ROSSI_ATT
GIALLI_ATT
VERDI_ATT
BIANCHI_ATT
NONESEG_ATT
TOT_ATT

ROSSI_TRATT
GIALLI_TRATT
VERDI_TRATT
BIANCHI_TRATT
TOT_TRATT

TOT_OB
TUTTI
```

---

## RF-09 – Posizione degli ospedali

Poiché il dataset degli accessi PS non contiene necessariamente coordinate utilizzabili direttamente, il sistema deve disporre di un piccolo dataset locale:

```text
ospedali.csv
```

contenente almeno:

```text
codice
nome
indirizzo
latitudine
longitudine
```

`codice` o `nome` devono permettere di collegare la struttura ai dati real-time provenienti dalla Regione Lazio.

Come per le Case della Comunità, le coordinate devono essere calcolate una volta e successivamente salvate.

---

## RF-10 – Visualizzazione dei Pronto Soccorso

Il sistema deve:

1. recuperare la situazione corrente dei PS;
2. associarla alle coordinate degli ospedali;
3. calcolare la distanza dell'ospedale dall'utente;
4. selezionare massimo **5 ospedali**;
5. visualizzarli inizialmente in ordine di distanza crescente.

Per ogni ospedale devono essere mostrati almeno:

**Nome ospedale**

Distanza: `X km`

In attesa:

```text
🔴 Rossi: X
🟡 Gialli: X
🟢 Verdi: X
⚪ Bianchi: X
❓ Non assegnati: X

Totale in attesa: X
```

Può inoltre essere visualizzato:

```text
Totale in trattamento: X
Totale presenti: X
Ultimo aggiornamento: ...
```

---

# 8. Ordinamento dei Pronto Soccorso

L'utente deve poter modificare l'ordinamento dei risultati.

Ordinamento predefinito:

```text
Distanza
```

Devono essere previste almeno le seguenti alternative:

```text
Distanza
Totale pazienti in attesa
Codici rossi in attesa
Codici gialli in attesa
Codici verdi in attesa
Codici bianchi in attesa
```

L'ordinamento deve agire esclusivamente sui 5 o sugli ospedali candidati individuati dal sistema.

Per semplicità nell'MVP **non deve essere calcolato un indice proprietario di "ospedale migliore"**.

Il sistema mostra informazioni oggettive e permette all'utente di confrontare distanza e situazione corrente.

---

# 9. Compatibilità problema–ospedale

La classificazione dell'LLM deve produrre una categoria generale del problema, ad esempio:

```text
GENERALE
TRAUMATOLOGICO
PEDIATRICO
OSTETRICO_GINECOLOGICO
ALTRO
```

Per il primo MVP questa informazione può essere mostrata all'utente senza realizzare un sistema complesso di matching delle specializzazioni ospedaliere.

Qualora sia disponibile nel dataset un'informazione affidabile sul `TIPO` del Pronto Soccorso, essa può essere utilizzata per escludere strutture chiaramente incompatibili.

La priorità dell'MVP deve rimanere:

```text
classificazione del bisogno
+
vicinanza
+
situazione PS in tempo reale
```

Il matching dettagliato tra patologia e specializzazione ospedaliera può essere considerato un'evoluzione successiva.

---

# 10. Interfaccia Streamlit

L'interfaccia deve essere molto semplice.

La pagina può essere suddivisa in:

### Area iniziale

Campi per:

```text
Età
Sesso
Peso
Altezza
Indirizzo
```

Pulsante:

```text
Inizia
```

### Chat

Successivamente deve comparire un'interfaccia simile a ChatGPT:

```text
Assistente:
Descrivi il problema che stai riscontrando.

Utente:
...

Assistente:
Da quanto tempo...?

Utente:
...
```

Al termine:

```text
In base alle informazioni fornite, la tipologia di struttura che
potrebbe essere più appropriata è:

CASA DELLA COMUNITÀ
```

seguita dall'elenco delle strutture.

---

# 11. Gestione errori

Il sistema deve gestire almeno:

* indirizzo non trovato;
* Groq non disponibile;
* risposta LLM non conforme al JSON;
* API Regione Lazio non disponibile;
* assenza di strutture vicine;
* dati PS mancanti;
* errore di geocodifica.

In caso di errore esterno deve essere mostrato un messaggio comprensibile e l'applicazione non deve terminare con eccezioni visibili all'utente.

---

# 12. Vincoli del prototipo

Per ridurre i tempi di sviluppo, l'MVP **non deve prevedere**:

* registrazione;
* login;
* profilo utente;
* storico delle richieste;
* database;
* machine learning predittivo;
* previsione dell'affluenza futura;
* cartella clinica;
* diagnosi;
* prescrizione di farmaci;
* prenotazione di visite;
* integrazione con sistemi ospedalieri;
* calcolo automatico dei tempi di attesa;
* algoritmi complessi di ottimizzazione.

I dati della singola conversazione possono essere mantenuti esclusivamente nello `session_state` di Streamlit.

---

# 13. File/dati necessari

Il progetto può quindi essere sviluppato utilizzando solamente quattro sorgenti dati:

| Dato                    | Fonte                                  | Utilizzo                    |
| ----------------------- | -------------------------------------- | --------------------------- |
| Accessi Pronto Soccorso | Open Data Regione Lazio                | Situazione PS real-time     |
| Farmacie                | Open Data Regione Lazio                | Ricerca farmacie vicine     |
| Case della Comunità     | CSV locale creato da fonti Regione/ASL | Ricerca CdC vicine          |
| Ospedali e coordinate   | CSV locale                             | Collegamento PS ↔ posizione |

Il file delle Case della Comunità può essere:

```text
data/case_comunita.csv
```

e quello degli ospedali:

```text
data/ospedali.csv
```

---

# 14. Flusso applicativo finale

```text
UTENTE
   │
   ▼
Inserimento dati personali + indirizzo
   │
   ├──► Geocoding ──► latitudine / longitudine
   │
   ▼
Descrizione problema
   │
   ▼
Groq LLM
   │
   ├── eventuali domande aggiuntive
   │
   ▼
Output JSON strutturato
   │
   ▼
Classificazione
   │
   ├───────────────┬──────────────────┐
   │               │                  │
   ▼               ▼                  ▼
FARMACIA      CASA COMUNITÀ      PRONTO SOCCORSO
   │               │                  │
   ▼               ▼                  ▼
Dataset         CSV locale        API Lazio
farmacie        CdC              real-time
   │               │                  │
   └───────┬───────┘                  │
           │                          │
           ▼                          ▼
    Calcolo distanza           Calcolo distanza
           │                          │
           ▼                          ▼
       TOP 5                      TOP 5 PS
           │                          │
           │                 ordinamento per:
           │                 distanza / rossi /
           │                 gialli / verdi /
           │                 bianchi / totale
           │                          │
           └────────────┬─────────────┘
                        ▼
                  RISULTATO UTENTE
```

---

# 15. Criterio di completamento dell'MVP

Il prototipo può essere considerato completato quando è possibile eseguire end-to-end il seguente scenario:

1. l'utente inserisce i propri dati;
2. inserisce un indirizzo;
3. descrive un problema;
4. Groq analizza il testo;
5. Groq può fare domande aggiuntive;
6. Groq restituisce un JSON valido;
7. il sistema classifica il bisogno come Farmacia, Casa della Comunità o Pronto Soccorso;
8. vengono calcolate le strutture più vicine;
9. vengono mostrate massimo 5 strutture;
10. nel caso del PS vengono visualizzati i dati real-time;
11. l'utente può cambiare l'ordinamento dei PS.

Questo rappresenta il perimetro dell'MVP da sviluppare.
