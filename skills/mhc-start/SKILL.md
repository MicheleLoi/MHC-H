---
name: mhc-start
description: Apre una sessione MHC governata. Genera un Session ID (SID) tramite il backend MHC e lo dichiara in chat per le skill successive. Da invocare una volta sola all'inizio di ogni conversazione di lavoro legale governato.
when_to_use: All'inizio di ogni conversazione in cui l'avvocato vuole lavorare sotto governance MHC (audit trail, decision_log, provenance). Va invocata PRIMA di /mhc-trace, /mhc-decision, /mhc-end.
allowed-tools:
  - WebFetch
---

# /mhc-start — Apertura sessione MHC

Apre una nuova sessione MHC governata sul backend `mhc.micheleloi.pro/cowork`. Il backend genera un Session ID (SID) univoco, persiste lo stato iniziale, e ritorna l'identificativo che le skill successive (`/mhc-trace`, `/mhc-decision`, `/mhc-end`) useranno come chiave di tracciamento.

Questa skill realizza la **Rule 1 (Gabriele)** — annunciare prima di azioni consequenziali: l'apertura di una sessione governata e l'inizio dell'audit trail vanno dichiarati esplicitamente all'avvocato. Senza SID dichiarato, le skill successive non hanno chiave di correlazione.

## Steps

1. Read env var `MHC_BEARER` (set at plugin install).
   - Se assente: errore *"Bearer key non configurato. Reinstalla il plugin dal welcome page del sito micheleloi.pro/accesso/."* Stop.
2. Read env var `MHC_API_BASE` (default `https://mhc.micheleloi.pro/cowork`).
3. Chiedi all'avvocato: *"Su quale pratica o progetto lavoriamo in questa sessione?"* Attendi risposta breve (es. *"Causa Rossi vs Bianchi"*, *"Parere DPO cliente Alfa"*, *"Revisione contratto fornitore"*). Salva come `project_name`.
4. Costruisci body JSON: `{"config_json": "{}", "project_name": "<project_name>"}`.
5. Compute audit signature: `hmac_sha256(MHC_BEARER, body_json)` hex.
   (Nota: niente SID ancora — la signature di /mhc-start usa solo bearer + body.)
6. WebFetch `POST <MHC_API_BASE>/api/sessions` con headers:
   - `Authorization: Bearer <MHC_BEARER>`
   - `MHC-Audit-Sig: <signature>`
   - `Content-Type: application/json`
   Body: `<body_json>`
7. Parse response JSON: estrai `sid` (e opzionalmente `state_json`).
   - Se risposta non-200: comunica all'avvocato *"Backend MHC non raggiungibile. Posso lavorare senza sessione — niente audit trail registrato. Riprova `/mhc-start` quando il servizio torna disponibile."* Stop.
   - Dichiara in chat: **"Sessione MHC aperta. SID = `<sid>`. Pratica: `<project_name>`."**
   - Salva `<sid>` come variabile conversation-context `MHC_SID` per le skill successive.
8. **Briefing rapido all'avvocato** (Three Principles + Seven Rules in versione operativa breve, una riga ciascuna):
   - *Apollo (assunzioni esplicite), Themis (autorità prima dell'azione), Fides (cita sempre la fonte).*
   - *Gabriele (annuncia), Salomone (offri scelte), Thot (scrivi le decisioni), Esdra (Approve/Edit/Cancel sugli artefatti), Dioscuri (umano + AI), Ockham (riusa), Minerva (mostra i contro).*
   - Chiudi con: *"Pronto a lavorare. Quando hai finito, digita `/mhc-end`. Per registrare una decisione cross-pratica, digita `/mhc-decision`. Per cristallizzare un insight, digita `/mhc-trace`."*

## Errori da NON commettere

- **Non creare file `.mhc-config.json` o simili sul filesystem dell'avvocato.** Lo stato di sessione vive nel backend MHC, non sul disco. Cowork non ha filesystem persistente lawyer-side.
- **Non invocare script Python o Bash.** Skill cowork = solo `WebFetch`.
- **Non procedere se `MHC_BEARER` è assente.** Senza bearer, niente sessione governata possibile.
- **Non inventare un SID provvisorio se il backend è irraggiungibile.** Comunica onestamente e proponi retry.

---

*mhc-start — parte di MHC-H plugin, AGPL v3*
