---
status: draft pending founder review
authored_by: pm @MHC-Work (Mode 3 SID-20260523-162500)
canon: _org/decision_log.md 2026-05-23 PM late — Naming canonical MHC-H
audience: utente RegIA non-tecnico (avvocati, ricercatori, policy makers, compliance, ecc.)
doctrine: no-terminale (founder 2026-05-23)
---

# Come installare e configurare MHC-H

*Per professionisti del lavoro intellettuale assistito da AI. Nessun comando
terminale, nessuna conoscenza tecnica richiesta.*

> **Versione canonica tecnica.** Questo `DISTRIBUZIONE.md` è il riferimento
> operativo per chi installa MHC-H. Per il quadro strategico vedi
> [micheleloi.pro/regia](https://micheleloi.pro/regia/) (quando la guida modulare
> sarà pubblicata) e il [README.md](README.md) di questo repo.

> **MHC-H** è uno dei tre prodotti del brand ombrello **RegIA**, insieme a
> **BeccarIA** (skill legali per l'avvocato italiano) e **Recode IT**
> (pseudonimizzazione web standalone). I tre moduli sono plug-and-play:
> ciascuno standalone, oppure combinabili a stack. Questo documento descrive
> l'installazione di MHC-H. Per gli altri due moduli vedi i rispettivi repo.

---

## Cosa è MHC-H

MHC-H è un **harness di governance per lavoro intellettuale assistito da AI**:
sessioni governate, audit trail append-only, dialectical reasoning,
output con provenance tracciata. Materializza il framework **Meaningful Human
Control** (Three Principles + Seven Rules) dentro Claude come plugin con
quattro skill MVP:

- `/mhc-start` — apre una sessione governata con Session ID univoco
- `/mhc-trace` — cristallizza un insight in un artefatto tracciato
- `/mhc-decision` — appende una decisione al log immutabile append-only
- `/mhc-end` — chiude la sessione e produce il transcript per archivio

Il plugin gira **in entrambe le modalità di Claude**: tab Cowork in Claude
Desktop (UI grafica, 5 click) **e** Claude Code Desktop. Il backend HTTP REST
è hostato su `api.mhc.regia.it`, autenticato con una Bearer key personale.

Per il razionale tecnico completo (perché AGPL, perché backend remoto, perché
audit signature HMAC) vedi il [README.md](README.md).

---

## Prerequisiti

- **App Claude installata sul tuo computer.** Scarica da
  [claude.com/download](https://claude.com/download) (installer Windows/macOS;
  vedi anche la [guida ufficiale Anthropic in italiano](https://code.claude.com/docs/it/desktop)).
  MHC-H si installa via interfaccia grafica — **nessun comando terminale richiesto**.
- **Piano Claude Pro o superiore.** Il piano gratuito non include plugin di terze parti.
- **Modalità consigliata: Cowork.** È la tab Cowork nella sidebar sinistra
  dell'app Claude, dove i plugin si installano in cinque click. È il percorso
  descritto sotto.
- **Anche supportato: Claude Code Desktop.** Stessa app, modalità alternativa
  di interazione. Il plugin MHC-H funziona anche lì.
- **Bearer key personale RegIA.** Free tier, no carta di credito.
  Vai su [micheleloi.pro/accesso/](https://micheleloi.pro/accesso/),
  inserisci la tua email, ricevi la chiave via posta. Tempo: <1 minuto.
  La stessa chiave funziona per MHC-H plugin e per il MCP server MHC-L Desktop
  (se in futuro ne avrai bisogno) — una chiave per utente.
- **Se non hai mai usato Claude**, può aiutarti vedere prima un tutorial
  introduttivo — ne segnalo alcuni in fondo (sezione "Tutorial guidato di
  terze parti").

---

## Installazione — percorso standard (GitHub marketplace)

> **Documentazione canonica del comando.** Il comando `/plugin marketplace add`
> è documentato ufficialmente da Anthropic in italiano qui:
> [Trova e installa plugin](https://code.claude.com/docs/it/discover-plugins).
> I cinque click descritti sotto sono la versione step-by-step pensata per chi
> non legge documentazione di software.

Questo è il percorso che useranno tutti gli utenti standard. Cinque click in
Claude Desktop.

1. **Apri Claude Desktop**, vai sulla tab **Cowork** nella sidebar sinistra.
2. Sempre nella sidebar di Cowork, clicca **Customize → Plugin → "+"** in alto
   a destra.
3. Nel menu che si apre clicca **"Crea plugin"** — sì, "Crea plugin", anche se
   non stai creando nulla: è il path UX counter-intuitivo per "aggiungere un
   marketplace esistente". (Noto gotcha dell'interfaccia Claude Desktop Pro
   standard a maggio 2026.)
4. Nel dialog **"Aggiungi marketplace"** incolla:

   ```
   https://github.com/MicheleLoi/MHC-H
   ```

   Premi **"Add"**.
5. Nella lista che compare, accanto a **"mhc-h"**, clicca **"Add plugin"**.

Fatto. Vedrai un messaggio di conferma. Dovrebbero comparire **4 skill**
installate: `/mhc-start`, `/mhc-trace`, `/mhc-decision`, `/mhc-end`.

### Stesso percorso in Claude Code Desktop

Se preferisci Claude Code Desktop, gli stessi due comandi funzionano direttamente
nella chat (Claude Code Desktop espone i comandi `/plugin` via chat):

```text
/plugin marketplace add MicheleLoi/MHC-H
/plugin install mhc-h@MHC-H
```

Il risultato è identico: 4 skill installate, pronte all'uso.

---

## Installazione — percorso alternativo (zip locale)

Per chi ha già una copia del plugin sul proprio computer (founder, tester
invitato, copia ricevuta via e-mail o cartella condivisa).

Path UI **diverso** dal precedente: si usa il pulsante **"Aggiungi plugin"**
(non "Aggiungi marketplace").

1. Claude Desktop → tab **Cowork** → **Customize → Plugin → "+"** in alto a
   destra.
2. Clicca **"Aggiungi plugin"**.
3. Seleziona il file zip del plugin sul tuo computer, ad esempio:

   ```
   C:\Users\<nome>\...\mhc-h-0.1.0-mvp.zip
   ```

4. Claude Desktop estrae e installa il plugin. Comparirà nella lista plugin
   con tag "Active".

In alternativa allo zip, al passo 4 della procedura standard puoi incollare il
**percorso assoluto della cartella locale** del repo (es.
`C:\Users\<nome>\MHC-H`) al posto dell'URL GitHub: il resto del flusso è
identico.

---

## Configurazione della Bearer key

Dopo l'installazione, MHC-H ha bisogno della tua Bearer key per parlare col
backend (`api.mhc.regia.it`). Senza key, le skill rispondono "Bearer non
configurato" e si fermano.

1. **Recupera la key dalla email RegIA** (vedi Prerequisiti).
   Subject tipico: *"La tua chiave MHC-H"*. La chiave ha formato
   `mhc_live_<32 caratteri alfanumerici>`.
2. **Apri le impostazioni plugin** in Claude Desktop:
   tab **Cowork** → **Customize → Plugin** → accanto a `mhc-h` clicca
   l'icona impostazioni (ingranaggio).
3. **Incolla la key** nel campo **`MHC_BEARER`**. Salva.
4. **(Opzionale)** Se devi puntare a un backend diverso da quello di default
   (`https://api.mhc.regia.it`), imposta anche **`MHC_API_BASE`** col tuo URL.
   Per uso standard ignora questo passo.

> **Single allowlist note.** MHC-H usa solo l'host `api.mhc.regia.it` per il
> backend, già documentato come dominio first-party RegIA. Nessun setup
> aggiuntivo richiesto sul `Network egress` di Claude Desktop nella maggior
> parte dei piani. Se il tuo piano enterprise ha l'allowlist non modificabile
> e blocca l'host, le skill restituiranno *"Backend non raggiungibile"* — in
> quel caso scrivimi via `mhcl@micheleloi.pro` e troviamo un workaround.

---

## Primo smoke test

Verifica che tutto sia connesso. Tempo: ~30 secondi.

1. **Apri una nuova conversazione Cowork** (con il plugin `mhc-h` attivo).
2. Digita:

   ```
   /mhc-start
   ```

3. **Atteso**: Claude apre una sessione, ti chiede il nome del progetto / pratica
   su cui stai lavorando, poi conferma:

   > *"Sessione MHC aperta. SID = `SID-YYYYMMDD-HHMMSS`. Pratica: `<nome>`."*

   Seguito da un breve briefing su Three Principles + Seven Rules.

4. Per chiudere il test, digita:

   ```
   /mhc-end
   ```

   La sessione viene sigillata sul backend. Risposta attesa:

   > *"Sessione `<SID>` sigillata."*

Se vedi entrambe le risposte, MHC-H è correttamente configurato. Sei pronto a
lavorare.

### Smoke test alternativo: append di una decisione

Per testare anche `/mhc-decision` (append-only audit trail):

1. Dopo `/mhc-start`, digita una proposizione esplicita di decisione, es.:

   > *"Decido di adottare AGPL per il nostro repo X. Alternative considerate:
   > MIT (troppo permissive per la nostra postura) e proprietary (incoerente
   > coi nostri valori). Rationale: coerenza filosofica con anti-fork."*

2. Poi digita:

   ```
   /mhc-decision
   ```

3. **Atteso**: Claude propone un'entry strutturata (topic, context, options,
   decision, rationale) e ti chiede **Approve / Edit / Cancel** prima di
   scrivere sul backend. Su Approve, ricevi un `decision_id` con conferma
   di immutabilità.

4. Chiudi con `/mhc-end`.

---

## Troubleshooting

### Non vedo "Crea plugin"

Questa opzione richiede piano Claude Pro o superiore. Verifica nelle
impostazioni del tuo account.

### Le skill rispondono "Bearer key non configurato"

Il plugin non vede la variabile `MHC_BEARER`. Riapri **Customize → Plugin →
impostazioni `mhc-h`**, verifica che la key sia incollata (no spazi prima/dopo,
formato `mhc_live_<...>`), salva e riprova.

### Le skill rispondono "Backend MHC non raggiungibile"

Possibili cause:

1. **Connessione internet assente.** Verifica.
2. **Host bloccato da policy di rete enterprise.** Apri *Impostazioni → Network
   egress* di Claude Desktop e verifica che `api.mhc.regia.it` sia raggiungibile.
   Se il piano blocca host first-party, contatta `mhcl@micheleloi.pro`.
3. **Backend temporaneamente down.** Lo trovi su tutte le installazioni
   contemporaneamente. Riprova fra qualche minuto, oppure scrivimi.

### Il plugin non risponde quando lancio `/mhc-start`

Vai su **Customize → Plugin** e verifica che accanto a `mhc-h` ci sia il tag
"Active". Se attivo ma non risponde, prova a essere esplicito nella richiesta:
*"usa la skill mhc-start"*. Se persiste, apri una issue su
[github.com/MicheleLoi/MHC-H/issues](https://github.com/MicheleLoi/MHC-H/issues).

### Errore "missing or invalid audit signature"

Errore lato backend — il client (skill) ha computato male l'HMAC. Non è un
problema di config tua. Riporta il caso via issue GitHub con il SID coinvolto
+ la skill che ha fallito (probabilmente `/mhc-decision` o `/mhc-trace`).

### Vedo solo 3 skill invece di 4

Probabile cache stale di Claude Desktop. Prova a fare logout + login, oppure
rimuovi + ri-aggiungi il plugin. In casi rari il marketplace remoto è ancora
su una versione precedente (es. il vecchio nome `mhc` invece di `mhc-h`):
in quel caso usa il percorso "zip locale" qui sopra.

---

## Tutorial guidato di terze parti

Se preferisci vedere Claude Code in azione prima di installarlo, ci sono alcuni
video YouTube in italiano che mostrano l'installazione e l'uso base. **Nessuno
copre specificamente MHC-H** — per quello segui le istruzioni in questo
documento.

- [Installazione Claude Code e primo utilizzo — tutorial semplice](https://www.youtube.com/watch?v=_mU3oQkkBQk)
- [Claude Code: La Guida COMPLETA per Iniziare nel 2026](https://www.youtube.com/watch?v=U57E3Ci94-A)
- [Installa CLAUDE CODE GRATIS sul tuo COMPUTER](https://www.youtube.com/watch?v=xfNDqZAG5N8)

Video di autori indipendenti — qualità dichiarata dai loro stessi titoli, non
da noi garantita. La documentazione canonica resta sempre
[code.claude.com/docs/it](https://code.claude.com/docs/it).

### Riferimenti ufficiali Anthropic in italiano

- [Applicazione desktop](https://code.claude.com/docs/it/desktop) — installer Windows/macOS
- [Guida rapida](https://code.claude.com/docs/it/quickstart) — primi passi CLI
- [Trova e installa plugin](https://code.claude.com/docs/it/discover-plugins) — pagina canonical su `/plugin marketplace add` e `/plugin install`

---

## Privacy

MHC-H opera **dentro la sandbox Claude**, isolata per conversazione. Le
cartelle che colleghi a una conversazione (in Cowork tab) sono visibili al
plugin; nient'altro del tuo computer lo è.

Le chiamate di rete del plugin vanno **solo** al backend `api.mhc.regia.it`,
con autenticazione Bearer e (per gli endpoint append-only) audit signature
HMAC-SHA256. Nessuna telemetria, nessun tracking, nessun analytics.

**Cosa il backend riceve e conserva:**

- *Sessioni* (`lawyer_sessions`): SID, project_name (etichetta che fornisci tu
  in `/mhc-start`), state_json (configurazione iniziale, vuota di default),
  timestamps.
- *Artefatti* (`artifacts`): il markdown reso da `/mhc-trace` con i campi
  che hai esplicitato durante la conversazione (insight, tensioni risolte,
  riferimenti). Contenuto provenance-tracked, owner-scoped (solo tu lo leggi).
- *Decisioni* (`decisions`): le entry append-only che approvi via `/mhc-decision`
  (topic, context, options, decision, rationale). Append-only by design — non
  modificabili, non cancellabili.

**Cosa il backend NON riceve:**

- Il transcript completo della tua conversazione con Claude (resta lato
  Anthropic, mai trasmesso a noi).
- File caricati nella conversazione (restano nella sandbox Claude).
- Metadati dell'host (IP non loggati per analytics; solo per debugging
  operativo VPS, comunque non conservati).

Il decision_log è la tua memoria audit-trail personale: la chiave per leggerlo
è la tua Bearer. Senza Bearer, nessuno accede ai tuoi dati.

---

## Licenza

**MHC-H è AGPL-3.0-only.** Vedi [`LICENSE-AGPL`](LICENSE-AGPL) per il testo
completo e [`NOTICE`](NOTICE) per le attribuzioni.

Razionale breve: un harness di governance/accountability è coerente solo con
una licenza che impone analoga accountability al software stesso. AGPL preserva
l'attribuzione del framework **Meaningful Human Control** (Three Principles +
Seven Rules) come research IP di Michele Loi.

**Importante:** AGPL governa solo il software MHC-H, **non** gli artefatti che
produci usando MHC-H. Le tue decisioni, traces, memo, draft restano di tua
proprietà integrale.

---

## Domande frequenti

**Che differenza c'è da Claude senza plugin?**
Senza plugin, Claude risponde ma non ha un audit trail strutturato delle tue
decisioni cross-progetto, né cristallizza ragionamenti come artefatti citabili,
né garantisce immutabilità di ciò che hai deciso. MHC-H aggiunge i quattro
strumenti minimi (start, trace, decision, end) per rendere il tuo lavoro
con AI accountable.

**Posso disinstallare il plugin?**
Sì, da **Customize → Plugin → Remove** accanto a `mhc-h`. I dati lato backend
restano (decisioni append-only, artefatti) — puoi sempre rilanciare l'install
e leggere il tuo decision log con la stessa Bearer key.

**MHC-H funziona offline?**
No. Il backend è remoto (`api.mhc.regia.it`). Senza rete, le skill
rispondono "Backend non raggiungibile". Per uso offline c'è MHC-L Desktop
(MCP server locale) — vedi repo separato.

**La stessa Bearer funziona per MHC-L Desktop?**
Sì, una chiave per utente per tutta la piattaforma RegIA.

**Come revoco la mia Bearer key?**
Scrivi a [noreply@mhc.regia.it](mailto:noreply@mhc.regia.it). Revoca immediata.

**Cosa è RegIA?**
RegIA è il brand ombrello / azienda che produce MHC-H + due altri moduli:
**BeccarIA** (skill legali, audience avvocato italiano) e **Recode IT**
(pseudonimizzazione web, audience consumer/prosumer). I tre moduli sono
plug-and-play. Vedi [micheleloi.pro/regia](https://micheleloi.pro/regia/)
per il quadro strategico.

---

*DISTRIBUZIONE.md — MHC-H v0.1.0-mvp — draft 2026-05-23, audience no-terminale
(Cowork primary + Claude Code Desktop secondario). Single backend host
(`api.mhc.regia.it`), single-step Bearer configuration. Per riferimenti canon
vedi MHC-Work `_org/decision_log.md` 2026-05-23 PM late §"Naming canonical:
MHC-H".*
