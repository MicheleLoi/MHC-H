---
name: mhc-end
description: Chiude la sessione MHC corrente. Il backend marca la sessione come ended e produce il transcript della conversazione come plugin output download. Applica Rule 3 — offre di registrare decisioni cross-pratica emerse non ancora catturate via /mhc-decision.
when_to_use: Quando l'avvocato vuole chiudere la sessione di lavoro, dice "ho finito", "chiudiamo qui", "/mhc-end", o equivalente. Da invocare PRIMA di chiudere la finestra cowork per garantire che la sessione sia stata sigillata sul backend.
allowed-tools:
  - WebFetch
---

# /mhc-end — Chiusura sessione MHC

Chiude la sessione MHC corrente. Il backend marca la sessione come `ended`, registra la lista degli artefatti prodotti, e (se supportato) restituisce il transcript della conversazione come download del plugin per archivio personale dell'avvocato.

Questa skill realizza la **Rule 3 (Thot)** — offre un'ultima occasione per scrivere ciò che resterebbe altrimenti non registrato: decisioni cross-pratica emerse in sessione non ancora catturate via `/mhc-decision`, insight non ancora cristallizzati via `/mhc-trace`.

## Steps

1. Read env var `MHC_BEARER` (set at plugin install).
   - Se assente: errore *"Bearer key non configurato. Reinstalla il plugin dal welcome page del sito mhc.regia.it."* Stop.
2. Read env var `MHC_API_BASE` (default `https://api.mhc.regia.it`).
3. Recupera `MHC_SID` dal conversation context.
   - Se assente: comunica *"Nessuna sessione MHC attiva da chiudere. Nessuna azione."* Stop.
4. **Rule 3 (Thot) — wrap-up check PRIMA della chiusura.** Chiedi all'avvocato:
   > *"Prima di chiudere la sessione `<MHC_SID>`, controllo: ci sono decisioni cross-pratica emerse oggi che non hai ancora registrato via `/mhc-decision`? Insight da cristallizzare via `/mhc-trace`?"*
   - Se l'avvocato indica decisioni/insight non registrati: invita a invocare `/mhc-decision` o `/mhc-trace` PRIMA di richiamare `/mhc-end`. Stop il wrap-up corrente.
   - Se l'avvocato conferma che è tutto registrato (o esplicitamente vuole chiudere senza ulteriori entries): procedi.
5. Chiedi all'avvocato una sintesi breve di chiusura: *"Sintesi della sessione in 1-2 frasi (per record di chiusura)?"* Salva come `goal`.
6. Componi il body:
   ```json
   {
     "goal": "<goal>",
     "artifacts_produced": ["<artifact_id 1>", "<artifact_id 2>", "..."],
     "exported": true
   }
   ```
   (`artifacts_produced` = lista dei `decision_id` + `artifact_id` ricordati dal conversation context delle invocazioni precedenti di `/mhc-decision` e `/mhc-trace` in questa sessione. Se non ne ricordi, lascia array vuoto `[]`.)
7. Compute audit signature: `hmac_sha256(MHC_BEARER, MHC_SID + body_json)` hex.
8. WebFetch `POST <MHC_API_BASE>/api/sessions/<MHC_SID>/end` con headers:
   - `Authorization: Bearer <MHC_BEARER>`
   - `MHC-Audit-Sig: <signature>`
   - `Content-Type: application/json`
   Body: `<body_json>`
9. Parse response: estrai `transcript_markdown` (se presente) e `ended_at`.
   - Se `transcript_markdown` è presente: presentalo all'avvocato come download del plugin con un'intro: *"Transcript della sessione `<MHC_SID>` esportato. Salvalo per archivio personale (es. dropbox studio, dossier cliente). Il backend conserva il record sigillato; il transcript leggibile è in questo download."*
   - Se il backend non restituisce un transcript (versione MVP backend senza conversation logging): comunica *"Sessione `<MHC_SID>` chiusa lato backend. Per archivio personale, copia manualmente la cronologia di questa conversazione dal pannello cowork — il backend conserva il record sigillato della sessione + artefatti, ma il transcript completo della chat resta solo lato claude.ai."*
10. Chiusura: *"Sessione `<MHC_SID>` sigillata. Per la prossima sessione, apri una nuova conversazione cowork e digita `/mhc-start`. A presto."*

## Errori da NON commettere

- **Non chiudere senza wrap-up check.** Saltare Rule 3 significa perdere decisioni cross-pratica che l'avvocato avrebbe voluto registrare ma non ha pensato a registrare.
- **Non invocare script Python o Bash per estrarre conversation history.** Cowork non ha JSONL filesystem-accessible; il transcript se esiste arriva dal backend.
- **Non sigillare due volte la stessa sessione.** Se il backend ritorna errore "session already ended", comunica all'avvocato e proponi `/mhc-start` per una nuova sessione.
- **Non promettere export del transcript se backend non lo supporta.** Nella MVP iniziale il backend può non conservare il transcript completo — sii onesto sul fatto che l'archivio del chat history è responsabilità del lawyer.

---

*mhc-end — parte di MHC-H plugin, AGPL v3*
