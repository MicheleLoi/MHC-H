---
name: mhc-trace
description: Cristallizza una tensione dialettica risolta o un insight emerso dalla conversazione come trace artifact governato, con frontmatter strutturato e provenance references. L'artifact viene persistito sul backend MHC e reso disponibile come download markdown.
when_to_use: Dopo brainstorming, esplorazione di alternative, o risoluzione di una tensione (es. "argomento causa vs settlement", "fee structure A vs B"), quando l'insight prodotto va preservato come artefatto citabile in sessioni future.
allowed-tools:
  - WebFetch
---

# /mhc-trace — Cristallizzazione trace epistemica

Crea un **trace artifact** dalla conversazione corrente. Un trace è la registrazione strutturata di un insight emerso da lavoro esplorativo: tensione dialettica risolta, mappa concettuale stabilizzata, formulazione raggiunta dopo iterazione. Il trace viene persistito sul backend MHC sotto il SID attivo, con frontmatter (titolo, data, SID, references) e contenuto markdown.

Questa skill realizza la **Rule 3 (Thot)** — *verba volant, scripta manent*: ciò che è stato compreso nella sessione va scritto, altrimenti svanisce quando la conversazione finisce.

## Steps

1. Read env var `MHC_BEARER` (set at plugin install).
   - Se assente: errore *"Bearer key non configurato. Reinstalla il plugin dal welcome page del sito mhc.regia.it."* Stop.
2. Read env var `MHC_API_BASE` (default `https://api.mhc.regia.it`).
3. Recupera `MHC_SID` dal conversation context (impostato da `/mhc-start`).
   - Se assente: comunica all'avvocato *"Nessuna sessione MHC attiva. Digita `/mhc-start` prima."* Stop.
4. **Rule 2 (Salomone) — surface meaningful choices.** Chiedi all'avvocato: *"Cosa va catturato in questo trace? Aiutami a distinguere — quale insight chiave, quale tensione è stata risolta, quali alternative considerate, quali domande restano aperte."* Attendi risposta.
5. Componi il body strutturato basandoti sulla conversazione + risposta dell'avvocato:
   ```json
   {
     "artifact_type": "trace",
     "session_id": "<MHC_SID>",
     "title": "<titolo descrittivo>",
     "content": {
       "key_insight": "<insight principale, 1-3 frasi>",
       "tension_resolved": "<tensione che ha trovato chiusura, o null>",
       "perspective_traces": ["<prospettive considerate>"],
       "inputs": ["<fonti, riferimenti, decisioni precedenti citate>"]
     }
   }
   ```
6. Compute audit signature: `hmac_sha256(MHC_BEARER, MHC_SID + body_json)` hex.
7. WebFetch `POST <MHC_API_BASE>/api/artifacts` con headers:
   - `Authorization: Bearer <MHC_BEARER>`
   - `MHC-Audit-Sig: <signature>`
   - `Content-Type: application/json`
   Body: `<body_json>`
8. Parse response: estrai `artifact_id` e `rendered_markdown`.
   - Presenta il markdown renderizzato all'avvocato in chat.
   - Comunica: *"Trace `<artifact_id>` creato e collegato alla sessione `<MHC_SID>`. Il markdown sopra è disponibile come download del plugin."*

## Errori da NON commettere

- **Non chiamare `/api/artifacts` senza SID.** Un trace orfano (senza sessione) non è auditable.
- **Non inventare il contenuto.** Il trace deve riflettere la conversazione reale — chiedi all'avvocato cosa va catturato, non dedurre.
- **Non saltare il rendering al lawyer.** L'avvocato deve vedere il markdown finale come conferma di cosa è stato registrato sul backend.

---

*mhc-trace — parte di mhc-cowork plugin, AGPL v3*
