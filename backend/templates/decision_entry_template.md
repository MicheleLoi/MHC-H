---
artifact_type: decision_entry
project: {{PROJECT_NAME}}
title: {{TITLE}}
topic: {{TOPIC}}
date: {{DATE}}
session_id: {{SESSION_ID}}
created_at: {{CREATED_AT}}
---

# Decision Entry — {{TITLE}}

<!--
mhc-cowork template: Decision Entry
Purpose: Append-only record of a single cross-domain decision
Rules: 2 (surface choices), 3 (write up), 4 (persist with template), Themis (authority chain)

Instructions for Claude:
- Read this template before creating — do not generate from memory
- One decision per entry. If multiple decisions emerged, create separate entries.
- Be specific about options considered — surface the alternatives before naming the choice
- Rationale should explain WHY, not just WHAT
- Decisions are append-only: once filed, never edited in place. Revisions go in a new entry that supersedes.
-->

---

## Topic

{{TOPIC}}

## Context

{{CONTEXT}}

## Options Considered

{{OPTIONS}}

## Decision

{{DECISION}}

## Rationale

{{RATIONALE}}

---

*Decision logged: {{CREATED_AT}}*
*mhc-cowork | append-only*
