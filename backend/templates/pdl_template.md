---
artifact_type: pdl
project: {{PROJECT_NAME}}
created: {{CREATED_DATE}}
last_updated: {{UPDATED_DATE}}
status: {{STATUS}}
session_id: {{SESSION_ID}}
inputs: []
validated: {{VALIDATED_TIMESTAMP}}
validation: {{approved / approved_with_edits}}
---

# Prompt Development Log (PDL)

<!--
mhc-cowork template: Prompt Development Log
Purpose: Document how a prompt/specification evolved
Rules: 2 (surface choices), 3 (write up), 4 (persist with template)

Instructions for Claude:
- Read this template before creating — do not generate from memory
- Each entry documents a decision point in prompt development
- Be specific about options considered - don't just list the chosen option
- Rationale should explain WHY, not just WHAT
- "What it affects" helps trace downstream impact
-->

---

## Development Entries

### PDL-001: {{ENTRY_TITLE}}

| Field | Value |
|-------|-------|
| Date | {{ENTRY_DATE}} |
| Issue/Need | {{ISSUE_ADDRESSED}} |

**Options Considered:**

1. **{{OPTION_1_NAME}}**: {{OPTION_1_DESCRIPTION}}
   - Pros: {{OPTION_1_PROS}}
   - Cons: {{OPTION_1_CONS}}

2. **{{OPTION_2_NAME}}**: {{OPTION_2_DESCRIPTION}}
   - Pros: {{OPTION_2_PROS}}
   - Cons: {{OPTION_2_CONS}}

**Decision:** {{DECISION_MADE}}

**Rationale:** {{RATIONALE}}

**What it affects:** {{DOWNSTREAM_IMPACT}}

---

### PDL-002: {{ENTRY_TITLE}}

<!-- Add more entries as the prompt evolves -->

| Field | Value |
|-------|-------|
| Date | {{ENTRY_DATE}} |
| Issue/Need | {{ISSUE_ADDRESSED}} |

**Options Considered:**

1. **{{OPTION_1_NAME}}**: {{OPTION_1_DESCRIPTION}}
2. **{{OPTION_2_NAME}}**: {{OPTION_2_DESCRIPTION}}

**Decision:** {{DECISION_MADE}}

**Rationale:** {{RATIONALE}}

**What it affects:** {{DOWNSTREAM_IMPACT}}

---

## Current Prompt State

<!-- Summary of where the prompt stands after all logged decisions -->

{{CURRENT_PROMPT_SUMMARY}}

---

*PDL generated: {{TIMESTAMP}}*
*mhc-cowork | Rules 2, 3, 4*
