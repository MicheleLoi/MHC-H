---
artifact_type: complete_prompt
project: {{PROJECT_NAME}}
version: {{VERSION}}
date: {{DATE}}
session_id: {{SESSION_ID}}
inputs: []
output_file: {{OUTPUT_FILE}}
validated: {{VALIDATED_TIMESTAMP}}
validation: {{approved / approved_with_edits}}
---

# Complete Prompt

<!--
MHC-H template: Complete Prompt
Purpose: Governing document for generation — the full specification
Rules: 1 (state intent), 4 (persist with template)

Instructions for Claude:
- Read this template before creating — do not generate from memory
- This is the consolidated specification for generating output
- Draw from epistemic traces and PDL entries
- Source mapping shows where each element came from (traceability)
- Be specific about constraints - vague guidance produces vague output
-->

---

### Purpose Statement
{{PURPOSE_STATEMENT}}

### Target Audience
{{TARGET_AUDIENCE}}

### Success Criteria
{{SUCCESS_CRITERIA}}

---

## Argument Architecture

<!-- The logical structure of what's being created -->

### Core Thesis
{{CORE_THESIS}}

### Supporting Arguments
1. {{ARGUMENT_1}}
2. {{ARGUMENT_2}}
3. {{ARGUMENT_3}}

### Anticipated Objections
- {{OBJECTION_1}}: {{RESPONSE_1}}
- {{OBJECTION_2}}: {{RESPONSE_2}}

---

## Section Specifications

### Section 1: {{SECTION_1_TITLE}}

| Attribute | Specification |
|-----------|---------------|
| Word Count | {{WORD_COUNT}} |
| Purpose | {{SECTION_PURPOSE}} |

**Must Accomplish:**
- [ ] {{MUST_1}}
- [ ] {{MUST_2}}
- [ ] {{MUST_3}}

**Key Points:**
{{KEY_POINTS}}

---

### Section 2: {{SECTION_2_TITLE}}

| Attribute | Specification |
|-----------|---------------|
| Word Count | {{WORD_COUNT}} |
| Purpose | {{SECTION_PURPOSE}} |

**Must Accomplish:**
- [ ] {{MUST_1}}
- [ ] {{MUST_2}}

**Key Points:**
{{KEY_POINTS}}

---

## Voice and Tone

### Register
{{REGISTER}} <!-- e.g., Academic, Professional, Conversational -->

### Tone
{{TONE}} <!-- e.g., Authoritative but accessible, Cautious, Bold -->

### Stylistic Notes
{{STYLISTIC_NOTES}}

---

## Constraints and Boundaries

### Must Include
- {{MUST_INCLUDE_1}}
- {{MUST_INCLUDE_2}}

### Must Avoid
- {{MUST_AVOID_1}}
- {{MUST_AVOID_2}}

### Word/Length Limits
{{LENGTH_LIMITS}}

---

## Source Mapping

<!-- Where did each element come from? This enables traceability. -->

| Element | Source | Reference |
|---------|--------|-----------|
| {{ELEMENT_1}} | {{SOURCE_1}} | {{REFERENCE_1}} |
| {{ELEMENT_2}} | {{SOURCE_2}} | {{REFERENCE_2}} |
| {{ELEMENT_3}} | {{SOURCE_3}} | {{REFERENCE_3}} |

---

*Complete Prompt generated: {{TIMESTAMP}}*
*MHC-H | Rules 1, 4*
*Sources: {{SOURCE_LIST}}*
