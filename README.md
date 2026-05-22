# MHC — Meaningful Human Control governance harness for AI-assisted knowledge work

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Status: MVP experimental](https://img.shields.io/badge/Status-MVP%20experimental-orange.svg)](#status)
[![Version: 0.1.0-mvp](https://img.shields.io/badge/Version-0.1.0--mvp-yellow.svg)](#status)

*Plugin Claude cowork + backend HTTP REST + website onboarding. Quattro skill MVP che orchestrano una sessione di lavoro intellettuale assistito da AI sotto governance esplicita: dichiarazione assunzioni, mappa autorita, citazioni grounding, decision_log append-only, output con provenance.*

> **Posizione strategica.** MHC e uno dei tre prodotti del brand ombrello **RegIA**, insieme a **Recode IT** (pseudonimizzazione web) e **BeccarIA** (legal AI ecosystem). I tre moduli sono plug-and-play: ciascuno standalone o combinabili a stack. MHC e il harness governance che orchestra il lavoro di chi usa AI in tasks intellettuali ad alta responsabilita.

---

## Cosa e MHC

MHC e un **framework di governance per lavoro intellettuale assistito da AI**. Distillato in tre principi epistemici (Apollo / Themis / Fides) e sette regole operative (Gabriele / Salomone / Thot / Esdra / Dioscuri / Ockham / Minerva), il framework risponde alla domanda: *come rendo auditable e accountable il lavoro che produco con un assistente AI?*

Il plugin cowork `mhc` istanzia questo framework dentro Claude. Apre una sessione governata (`/mhc-start`), permette di cristallizzare ragionamenti in artefatti tracciati (`/mhc-trace`), registra decisioni in un log append-only consultabile retrospettivamente (`/mhc-decision`), e chiude la sessione con export integrale del transcript (`/mhc-end`). Ogni POST al backend e firmato con audit signature HMAC; il decision_log e append-only by design — non e possibile sovrascrivere o cancellare entry passate.

**Domain-agnostic.** A differenza di BeccarIA (legal-specific) o Recode IT (pseudonymization-specific), MHC e una disciplina di governance applicabile cross-dominio. Il framework non assume un dominio professionale specifico.

## Per chi

- **Avvocati** che vogliono audit trail consultabile dal bar disciplinare
- **Ricercatori accademici** che producono draft assistiti da AI e devono dichiarare il workflow al peer review
- **Medical peer reviewers** che valutano paper con AI assistance e devono provenance-track il giudizio
- **Policy makers** che redigono opinioni di policy dove la decisione finale richiede authority chain mappata
- **Engineering teams** che documentano ADR (Architecture Decision Records) con dialectical reasoning preservato
- **Journalisti** che producono pezzi con AI assistance e devono citation-track le fonti
- **Compliance officers** che gestiscono review processes con accountability traceable
- **Therapists / clinicians** in supervision settings dove decisioni cliniche assistite da AI richiedono trace

In una frase: **chi sente bisogno di accountability traceable nel proprio lavoro intellettuale**.

## Architettura 5-layer (target post-merge)

MHC fa parte di un bundle architettonico modulare:

- **Layer 0** — Website onboarding `mhc.regia.it` (ceremonial intro al framework + signup tier free)
- **Layer 1** — Cowork plugin `mhc` (4 skill MVP: start / trace / decision / end)
- **Layer 2** — Backend HTTP REST `api.mhc.regia.it` (sessions, artifacts, decisions, audit signature)
- **Layer 3** — **Recode IT** (pseudonimizzazione web standalone, gia live su `recode.micheleloi.pro`)
- **Layer 4** — **BeccarIA** (legal AI ecosystem cowork plugin standalone, gia live su `legal-tech-cowork`)

I quattro layer post-MHC sono plug-and-play: il lawyer puo usare Recode IT senza MHC, BeccarIA senza MHC, MHC senza Recode IT, etc. Il bundle e l'orchestrazione, non il lock-in.

## Installazione

Due click guidati dentro Claude Code Desktop:

```text
/plugin marketplace add MicheleLoi/mhc-cowork
/plugin install mhc@mhc-cowork
```

**Setup Bearer key.** Il plugin chiama il backend `api.mhc.regia.it` con Bearer auth. Per ottenere la key:

1. Naviga a [mhc.regia.it/signup](https://mhc.regia.it/signup) (free email-only tier MVP)
2. Inserisci email; ricevi link welcome via mail
3. Copia Bearer key dalla welcome page nella plugin config

Tier MVP: free email-only. Tier paid (post-MVP, opzionale per casi enterprise / heavy usage) attivabile via Stripe checkout.

Prima volta con Claude Code Desktop? Vedi [code.claude.com/docs/it/desktop](https://code.claude.com/docs/it/desktop).

## Le quattro skill MVP

1. **`/mhc-start`** — Apre sessione governata. Backend allocata SID univoco, dichiarata in chat. Setup esplicito di scope sessione, dominio task, autorita decision-maker.

2. **`/mhc-trace`** — Cristallizza un ragionamento esplorativo in artefatto tracciato. Markdown reso con header metadata (SID, timestamp, autore), persistito server-side con audit signature.

3. **`/mhc-decision`** — Append entry al decision_log append-only. Format: topic + context + options enumerate + decision + rationale. Una volta scritta, l'entry e immutabile.

4. **`/mhc-end`** — Chiude sessione. Backend marca sessione terminata; conversation export disponibile per download (markdown integrale del transcript). Idempotente: una sessione chiusa non puo riaprirsi.

## Status

**MVP experimental — 0.1.0-mvp.**

Questo plugin e in fase di validazione con un piccolo gruppo di lawyer-tester. **NOT production-ready.** Lawyer-tester validation pending (Fase 4 del plan canonico). Acceptance criteria per merge a RegIA main bundle: ≥3/4 obiettivi MVP rate ≥4/5 Likert su decision_log + provenance + ritual onboarding + composability.

Se gli acceptance criteria non reggono al lawyer-test, MHC restera **tool interno founder** in MHC-Work (non product line RegIA). Trasparenza esplicita: questa e una sperimentazione, non un commitment commerciale.

## License

**AGPL-3.0-only.** Vedi `LICENSE-AGPL` per il testo completo e `NOTICE` per attribuzioni.

Razionale AGPL (in breve):

- **Coerenza filosofica** — un framework di governance/accountability discipline e coerente solo con una licenza che impone analoga accountability al software stesso (copyleft network use clause)
- **Anti-fork-and-strip-credit protection** — il framework Three Principles + Seven Rules e research IP di Michele Loi; AGPL preserva attribution downstream
- **Coerenza ecosystem** — BeccarIA AGPL + ecosystem legal-AI open source dominante AGPL (MikeOSS lineage)
- **Output del lawyer NON sono coperti** — AGPL governa solo il software MHC, NON gli artefatti prodotti usando MHC (memo, decision log entries, draft, output rendered restano proprieta integrale del lawyer/user)
- **Dual-licensing commerciale** — opzionale post-MVP per casi enterprise specifici (pattern MongoDB / MariaDB); contatto founder per discutere

## Related projects

- **Recode IT** — Pseudonimizzazione web standalone (Layer 3 del bundle RegIA): [recode.micheleloi.pro](https://recode.micheleloi.pro)
- **BeccarIA** — Legal AI ecosystem cowork plugin standalone (Layer 4 del bundle RegIA): [github.com/MicheleLoi/legal-tech-cowork](https://github.com/MicheleLoi/legal-tech-cowork)

## Founder

**Michele Loi** — research lineage AI governance, framework author Meaningful Human Control.

Contatto: [mhcl@micheleloi.pro](mailto:mhcl@micheleloi.pro)

---

# MHC — Meaningful Human Control governance harness (English summary)

*Claude cowork plugin + HTTP REST backend + onboarding website. Four MVP skills that orchestrate AI-assisted intellectual work under explicit governance: declared assumptions, mapped authority chain, grounded citations, append-only decision log, provenance-tracked output.*

MHC is one of three products under the **RegIA** umbrella brand, alongside **Recode IT** (web-based pseudonymization) and **BeccarIA** (Italian legal-AI ecosystem cowork plugin). Plug-and-play modules: each standalone or combined as a stack. MHC is the governance harness that orchestrates work for those who use AI in high-responsibility intellectual tasks.

**The framework.** Three epistemic principles (Apollo / Themis / Fides) plus seven operational rules (Gabriele / Salomone / Thot / Esdra / Dioscuri / Ockham / Minerva). Domain-agnostic: applicable to lawyers, researchers, medical peer reviewers, policy makers, engineering ADR, journalism, compliance officers.

**MVP skills (v0.1.0-mvp):** `/mhc-start` (open governed session) — `/mhc-trace` (crystallize reasoning into traced artifact) — `/mhc-decision` (append entry to append-only decision log) — `/mhc-end` (close session + transcript export).

**Status:** MVP experimental, NOT production-ready. Lawyer-tester validation pending. Merge to main RegIA bundle conditional on acceptance criteria from canonical plan.

**License:** AGPL-3.0-only. The framework "Meaningful Human Control" (Three Principles + Seven Rules) is research IP authored by Michele Loi. Use of the framework name in derivative works should preserve attribution to Loi's research lineage. AGPL governs only MHC software, NOT artifacts produced by users (memos, decision logs, drafts remain users' property).
