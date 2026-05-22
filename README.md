# MHC — Meaningful Human Control governance harness for AI-assisted knowledge work

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Status: MVP experimental](https://img.shields.io/badge/Status-MVP%20experimental-orange.svg)](#status)
[![Version: 0.1.0-mvp](https://img.shields.io/badge/Version-0.1.0--mvp-yellow.svg)](#status)

*Claude cowork plugin + HTTP REST backend. Quattro skill MVP che orchestrano una sessione di lavoro intellettuale assistito da AI sotto governance esplicita: dichiarazione assunzioni, mappa autorità, citazioni grounding, decision_log append-only, output con provenance.*

> **Posizione strategica.** MHC è uno dei tre prodotti del brand ombrello **RegIA**, insieme a **BeccarIA** (skill legali per l'avvocato italiano nell'ecosistema legal-AI open source) e **Recode IT** (pseudonimizzazione web standalone). I tre moduli sono plug-and-play: ciascuno standalone o combinabili a stack. MHC è il harness governance, applicabile cross-dominio, per chi usa AI in tasks intellettuali ad alta responsabilità.

---

## Cosa è MHC

MHC è un **framework di governance per lavoro intellettuale assistito da AI**. Distillato in tre principi epistemici (Apollo / Themis / Fides) e sette regole operative (Gabriele / Salomone / Thot / Esdra / Dioscuri / Ockham / Minerva), risponde alla domanda: *come rendo auditable e accountable il lavoro che produco con un assistente AI?*

Il plugin cowork `mhc` istanzia questo framework dentro Claude. Apre una sessione governata (`/mhc-start`), permette di cristallizzare ragionamenti in artefatti tracciati (`/mhc-trace`), registra decisioni in un log append-only consultabile retrospettivamente (`/mhc-decision`), e chiude la sessione con export integrale del transcript (`/mhc-end`). Ogni richiesta al backend è firmata con audit signature HMAC; il decision_log è append-only by design — non è possibile sovrascrivere o cancellare entry passate.

**Domain-agnostic.** Il framework non assume un dominio professionale specifico.

## Per chi

Chi sente il bisogno di **accountability tracciabile** nel proprio lavoro intellettuale, in particolare:

- Avvocati che vogliono audit trail consultabile
- Ricercatori che producono draft assistiti da AI e devono dichiarare il workflow al peer review
- Medical peer reviewers che valutano paper con AI assistance
- Policy makers che redigono opinioni dove la decisione richiede authority chain mappata
- Engineering teams che documentano Architecture Decision Records con dialectical reasoning preservato
- Journalisti che producono pezzi con AI assistance e devono citation-track le fonti
- Compliance officers che gestiscono review processes
- Therapists / clinicians in supervision settings con decisioni cliniche assistite da AI

## Installazione

Due comandi guidati dentro Claude Code Desktop:

```text
/plugin marketplace add MicheleLoi/mhc-cowork
/plugin install mhc@mhc-cowork
```

**Setup Bearer key.** Il plugin chiama un backend REST con Bearer auth. Per ottenere una key gratuita (tier free, no carta di credito): `https://mhc.micheleloi.pro/accesso/` — signup email-only, ricevi key via mail, paste in config plugin.

La stessa Bearer key dà accesso al plugin `mhc` cowork e al MCP server MHC-L Desktop. Una key per utente.

## Le quattro skill MVP

1. **`/mhc-start`** — Apre sessione governata. Backend alloca SID univoco. Setup esplicito di scope sessione, dominio task, autorità decision-maker.
2. **`/mhc-trace`** — Cristallizza un ragionamento esplorativo in artefatto tracciato. Markdown reso con header metadata, persistito server-side con audit signature.
3. **`/mhc-decision`** — Append entry al decision_log append-only. Format: topic + context + options + decision + rationale. Una volta scritta, l'entry è immutabile.
4. **`/mhc-end`** — Chiude sessione. Backend marca sessione terminata; conversation export disponibile per download. Idempotente.

## Status

**MVP experimental — versione 0.1.0-mvp.**

In fase di validazione con tester invitati. NOT production-ready. Feedback su bug, gap di usabilità, suggerimenti di scope: vedi sezione [Founder](#founder).

## License

**AGPL-3.0-only.** Vedi `LICENSE-AGPL` per il testo completo e `NOTICE` per attribuzioni.

Razionale AGPL:

- **Coerenza filosofica** — un framework di governance/accountability discipline è coerente solo con una licenza che impone analoga accountability al software stesso
- **Anti-fork-and-strip-credit** — il framework Three Principles + Seven Rules è research IP di Michele Loi; AGPL preserva attribution downstream
- **Coerenza con l'ecosistema open source legal-AI** dove AGPL è la postura dominante
- **Output dell'utente NON sono coperti** — AGPL governa solo il software MHC, NON gli artefatti prodotti usando MHC (memo, decision log entries, draft, output rendered restano proprietà integrale dell'utente)
- **Dual-licensing commerciale** — opzionale post-MVP per casi enterprise specifici; contattare il founder per discutere

## Related projects

- **Recode IT** — Pseudonimizzazione web standalone: [recode.micheleloi.pro](https://recode.micheleloi.pro)
- **BeccarIA** — Legal AI ecosystem cowork plugin standalone: [github.com/MicheleLoi/legal-tech-cowork](https://github.com/MicheleLoi/legal-tech-cowork)

## Founder

**Michele Loi** — research lineage AI governance, framework author Meaningful Human Control.

Contatto: [mhcl@micheleloi.pro](mailto:mhcl@micheleloi.pro)

---

# MHC — Meaningful Human Control governance harness (English summary)

*Claude cowork plugin + HTTP REST backend. Four MVP skills that orchestrate AI-assisted intellectual work under explicit governance: declared assumptions, mapped authority chain, grounded citations, append-only decision log, provenance-tracked output.*

**The framework.** Three epistemic principles (Apollo / Themis / Fides) plus seven operational rules (Gabriele / Salomone / Thot / Esdra / Dioscuri / Ockham / Minerva). Domain-agnostic: applicable to lawyers, researchers, medical peer reviewers, policy makers, engineering ADR, journalism, compliance officers.

**MVP skills (v0.1.0-mvp):** `/mhc-start` (open governed session) — `/mhc-trace` (crystallize reasoning into traced artifact) — `/mhc-decision` (append entry to append-only decision log) — `/mhc-end` (close session + transcript export).

**Status:** MVP experimental, NOT production-ready. Feedback and bug reports welcome via founder contact.

**License:** AGPL-3.0-only. The framework "Meaningful Human Control" (Three Principles + Seven Rules) is research IP authored by Michele Loi. Use of the framework name in derivative works should preserve attribution to Loi's research lineage. AGPL governs only MHC software, NOT artifacts produced by users (memos, decision logs, drafts remain users' property).
