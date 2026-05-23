---
artifact_type: draft
project: {{PROJECT_NAME}}
title: {{TITLE}}
draft_type: {{DRAFT_TYPE}}
date: {{DATE}}
session_id: {{SESSION_ID}}
upstream_refs: {{UPSTREAM_REFS_YAML}}
---

# {{TITLE}}

<!--
MHC-H template: Draft
Purpose: A provenance-tracked document draft (memo, brief, letter, spec, etc.)
Rules: 3 (write up), 4 (persist with template), Fides (cite sources)

Instructions for Claude:
- Read this template before creating — do not generate from memory
- The "upstream_refs" field lists the artifact_ids this draft draws from
  (decisions, traces, notes, prior drafts). Provenance trail.
- If the draft is a revision of a prior draft, list the prior artifact_id in
  upstream_refs and consider opening a modlog alongside.
-->

---

## Upstream References

{{UPSTREAM_REFS_MD}}

---

## Draft

{{CONTENT}}

---

*Draft created: {{TIMESTAMP}}*
*MHC-H | provenance-tracked*
