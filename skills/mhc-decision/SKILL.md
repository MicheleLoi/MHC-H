---
name: mhc-decision
description: Registra una decisione cross-pratica (practice-level o case-level) nel decision_log eternal append-only del lawyer. Audit trail per protezione bar disciplinare + knowledge management cross-case. Niente UPDATE possibile — solo APPEND.
when_to_use: Quando l'avvocato ratifica una decisione che attraversa più pratiche o che fissa una direzione (accettare un cliente, fee structure, partner cross-disciplina, policy studio; argomento causa, settlement vs trial, escalation). Nello STESSO TURNO della ratifica — non differita.
allowed-tools:
  - WebFetch
---

# /mhc-decision — Registrazione decisione append-only

Appende una **decision entry** al decision_log governato del lawyer. Il decision_log è memoria trasversale append-only delle scelte che hanno impatto su più pratiche o che fissano la policy professionale dello studio. La persistenza è eternal: una volta scritta, l'entry non si modifica più. Se la decisione si rivela errata, si appende una nuova entry che la supersede — la storia precedente resta come record immutabile.

Questa skill realizza la **Rule 4 (Esdra)** — *proba omnia*: ogni decisione registrata è prima mostrata all'avvocato come testo strutturato, e solo dopo conferma esplicita viene persistita. Il backend rifiuta UPDATE per garanzia di immutabilità.

## Quando questa skill applies

- L'avvocato ha **appena ratificato** una decisione in conversazione.
- La decisione affetta più di una pratica, fissa una direzione strategica dello studio, ratifica una proposta esterna, o supersede una posizione precedente.

**Non usare per:** decisioni intra-pratica (vanno in note di causa o modlog interno), scelte operative quotidiane, decisioni reversibili in 5 minuti.

## Steps

1. Read env var `MHC_BEARER` (set at plugin install).
   - Se assente: errore *"Bearer key non configurato. Reinstalla il plugin dal welcome page del sito mhc.regia.it."* Stop.
2. Read env var `MHC_API_BASE` (default `https://api.mhc.regia.it`).
3. Recupera `MHC_SID` dal conversation context (impostato da `/mhc-start`).
   - Se assente: comunica *"Nessuna sessione MHC attiva. Digita `/mhc-start` prima — il decision_log richiede SID per tracciabilità."* Stop.
4. Componi l'entry strutturata dalla conversazione:
   ```json
   {
     "sid": "<MHC_SID>",
     "topic": "<titolo breve della decisione>",
     "context": "<cosa ha innescato la decisione, 1-2 frasi>",
     "options": ["<alternativa A>", "<alternativa B>", "..."],
     "decision": "<cosa è stato deciso — verbatim ratifica dell'avvocato quando possibile>",
     "rationale": "<perché questa e non le alternative>"
   }
   ```
5. **Rule 4 (Esdra) — Approve / Edit / Cancel — OBBLIGATORIO PRIMA DEL POST.**
   Mostra all'avvocato l'entry strutturata in formato leggibile:
   ```
   ────────────────────────────────────────────
   Decisione da registrare nel decision_log:

   Topic:      <topic>
   Contesto:   <context>
   Alternative: <options>
   Decisione:  <decision>
   Rationale:  <rationale>

   Sessione:   <MHC_SID>
   ────────────────────────────────────────────

   Append-only: una volta registrata, non si modifica più.
   [ Approve ]  [ Edit ]  [ Cancel ]
   ```
   - **Edit:** chiedi all'avvocato cosa modificare, ricomponi l'entry, ripresenta il prompt Approve/Edit/Cancel.
   - **Cancel:** comunica *"Decisione non registrata. Nessuna modifica al decision_log."* Stop.
   - **Approve:** procedi a step 6.
6. Compute audit signature: `hmac_sha256(MHC_BEARER, MHC_SID + body_json)` hex.
7. WebFetch `POST <MHC_API_BASE>/api/decisions` con headers:
   - `Authorization: Bearer <MHC_BEARER>`
   - `MHC-Audit-Sig: <signature>`
   - `Content-Type: application/json`
   Body: `<body_json>`
8. Parse response: estrai `decision_id`.
   - Comunica all'avvocato: *"Decisione registrata. `decision_id = <decision_id>`. Append-only confermato — l'entry resta immutabile come parte del tuo audit trail professionale."*
   - Se la decisione supersede una precedente, ricorda all'avvocato: *"Se questa supersede una decisione precedente, la storia di quella resta nel log come record storico — la nuova entry indica solo la direzione corrente."*

## Cosa questa skill NON fa

- **Non modifica entry esistenti.** Backend rifiuta PUT/DELETE su `/api/decisions` per design. Append-only è hard rule.
- **Non chiude tensioni automaticamente.** Se la decisione risolve una tensione dialettica, l'avvocato può crearne un trace separato via `/mhc-trace`.
- **Non aggiorna altri sistemi del lawyer.** La persistenza è solo backend MHC; eventuali sincronizzazioni col gestionale studio sono responsabilità del lawyer.

## Errori da NON commettere

- **Saltare Rule 4 (Approve/Edit/Cancel).** L'append è irreversibile — l'avvocato deve confermare esplicitamente.
- **Inventare context o rationale.** Se l'avvocato non li ha articolati, chiedi prima di comporre l'entry.
- **Procedere senza SID.** Senza SID, l'entry non è collegata a una sessione e perde tracciabilità.

---

*mhc-decision — parte di mhc-cowork plugin, AGPL v3*
