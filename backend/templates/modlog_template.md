---
artifact_type: modlog
document: {{DOCUMENT_NAME}}
output_file: {{OUTPUT_FILE}}
project: {{PROJECT_NAME}}
created: {{CREATED_DATE}}
last_updated: {{UPDATED_DATE}}
session_id: {{SESSION_ID}}
inputs: []
validated: {{VALIDATED_TIMESTAMP}}
validation: {{approved / approved_with_edits}}
---

# Modification Log

<!--
MHC-H template: Modification Log
Purpose: Track intellectual decisions during revision
Rules: 2 (surface choices), 3 (write up), 4 (persist with template)

Instructions for Claude:
- Read this template before creating — do not generate from memory
- Each entry documents a substantive change (not typos/formatting)
- Type categorization helps identify patterns in how work evolves
- Focus on the intellectual decision, not the mechanical edit
- "note" is optional — only include when there is a meaningful quote or clarification
-->

---

## Modification Entries

### MOD-001

| Field | Value |
|-------|-------|
| Date | {{MOD_DATE}} |
| Type | {{MOD_TYPE}} |

<!--
Type options — text documents (papers, drafts, specs, prompts):
- Conceptual Restructure: Changed how ideas are organized or related
- Epistemic Calibration: Adjusted certainty levels, hedging, claims
- Scope Adjustment: Added or removed content areas
- Strategic Reorientation: Changed approach or direction
- Clarification: Made existing content clearer without changing meaning
- Evidence Update: Added, removed, or changed supporting material

Type options — software artifacts (scripts, configs, skill files, templates):
- Bug Fix: Corrected incorrect behavior
- Logic Correction: Changed how something works (not just why)
- Behavioral Change: Adjusted what the artifact does in a specific case
- Interface Change: Changed how the artifact is called or what it returns
- Scope Trim: Deliberately removed a section or feature
-->

**Change:**
{{CHANGE}}

**Rationale:**
{{RATIONALE}}

---

<!-- ENTRIES_END -->

*Modification Log generated: {{TIMESTAMP}}*
*MHC-H | Rules 2, 3, 4*
