# Part of MHC-H. AGPL v3 — see LICENSE-AGPL
"""
templates.py — Template loader for the MHC-H backend.

Reads template files from templates/ (bundled with this package). Original
fill functions (note, trace, pdl, modlog, product_dev_log, session_log,
prompt) are ported verbatim from the MHC-L MCP server. Two new fill
functions (decision_entry, draft) are added for the MHC-H MVP.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Template filenames by artifact_type
TEMPLATE_FILES: Dict[str, str] = {
    "note": "note_template.md",
    "trace": "epistemic_trace_template.md",
    "pdl": "pdl_template.md",
    "product_dev_log": "product_dev_log_template.md",
    "modlog": "modlog_template.md",
    "session_log": "session-log-template.md",
    "prompt": "complete_prompt_template.md",
    # MHC-H additions
    "decision_entry": "decision_entry_template.md",
    "draft": "draft_template.md",
}


def load_template(artifact_type: str) -> Optional[str]:
    """Read raw template text for the given artifact type.

    Returns None if the type is unknown or the file is missing.
    """
    filename = TEMPLATE_FILES.get(artifact_type)
    if not filename:
        return None
    template_path = Path(__file__).parent / "templates" / filename
    if not template_path.exists():
        return None
    return template_path.read_text(encoding="utf-8")


def _yaml_safe(value: Any) -> str:
    """Return a YAML-safe scalar representation of value.

    Double-quotes (with escaping) any string that would break a plain YAML
    scalar — specifically when it contains ': ' (which YAML reads as a
    nested mapping indicator), starts with a flow indicator, or is empty.
    """
    if value is None:
        return '""'
    if not isinstance(value, str):
        value = str(value)
    needs_quote = (
        value == ""
        or ": " in value
        or value.endswith(":")
        or value.startswith(("#", "&", "*", "!", "|", ">", "'", '"', "%", "@", "`"))
        or (value and value[0].isspace())
        or (value and value[-1].isspace())
    )
    if not needs_quote:
        return value
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _normalize_options(options: Any) -> list:
    """Accept options as list[dict], list[str], str, dict, or None.

    Returns list[dict] with at least {name, description}, preserving pros/cons
    if present. Graceful degradation for callers that don't know the expected
    sub-structure.
    """
    if not options:
        return []
    if isinstance(options, dict):
        return [options]
    if isinstance(options, str):
        # Try splitting on blank lines first, then on "; ".
        parts = [p.strip() for p in re.split(r"\n\s*\n", options) if p.strip()]
        if len(parts) <= 1:
            parts = [p.strip() for p in options.split(";") if p.strip()]
        if not parts:
            parts = [options.strip()]
        return [{"name": f"Option {i}", "description": p} for i, p in enumerate(parts, 1)]
    if isinstance(options, list):
        normalized: list = []
        for i, opt in enumerate(options, 1):
            if isinstance(opt, dict):
                normalized.append(opt)
            elif isinstance(opt, str):
                normalized.append({"name": f"Option {i}", "description": opt})
            else:
                normalized.append({"name": f"Option {i}", "description": str(opt)})
        return normalized
    return [{"name": "Option 1", "description": str(options)}]


def _list_to_yaml(items: list) -> str:
    """Render a Python list as inline YAML (e.g. [] or [a, b])."""
    if not items:
        return "[]"
    quoted = [_yaml_safe(i) for i in items]
    return "[" + ", ".join(quoted) + "]"


def fill_note(
    session_id: str,
    project_name: str,
    title: str,
    content: Dict[str, Any],
) -> str:
    """Fill the note template with the provided fields."""
    template = load_template("note")
    if template is None:
        raise ValueError("note_template.md not found in templates/")

    note_id = content.get("note_id", "NOTE_XXX")
    body = content.get("body", "")
    context_text = content.get("context", "")
    inputs = content.get("inputs", [])
    links = content.get("links", [])
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    ts_str = now.strftime("%Y-%m-%dT%H:%M:%S")

    inputs_yaml = _list_to_yaml(inputs)
    links_text = "\n".join(f"- {l}" for l in links) if links else "- (none yet)"

    result = template
    result = result.replace("NOTE_[XXX]", note_id)
    result = result.replace(
        "title: [Brief Title]",
        f"title: {_yaml_safe(title)}",
        1,
    )
    result = result.replace(
        "project: [Project name]",
        f"project: {_yaml_safe(project_name)}",
        1,
    )
    result = result.replace(
        "context: [What prompted this note? Optional.]",
        f"context: {_yaml_safe(context_text or '(not specified)')}",
        1,
    )
    result = result.replace("[Brief Title]", title)
    result = result.replace("[Project name]", project_name)
    result = result.replace("[YYYY-MM-DD]", date_str)
    result = result.replace("[SID-YYYYMMDD-HHMMSS]", session_id)
    result = result.replace("inputs: []", f"inputs: {inputs_yaml}")
    result = result.replace("[YYYY-MM-DDTHH:MM:SS]", ts_str)
    result = result.replace("[approved / approved_with_edits]", "approved")

    body_placeholder = re.search(
        r"\[The note itself\..*?\]",
        result,
        re.DOTALL,
    )
    if body_placeholder:
        result = result[: body_placeholder.start()] + body + result[body_placeholder.end():]

    links_placeholder = re.search(
        r"\[List artifacts.*?\]",
        result,
        re.DOTALL,
    )
    if links_placeholder:
        result = (
            result[: links_placeholder.start()]
            + links_text
            + result[links_placeholder.end():]
        )

    return result


def fill_trace(
    session_id: str,
    project_name: str,
    title: str,
    content: Dict[str, Any],
) -> str:
    """Fill the epistemic trace template."""
    template = load_template("trace")
    if template is None:
        raise ValueError("epistemic_trace_template.md not found in templates/")

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    ts_str = now.strftime("%Y-%m-%dT%H:%M:%S")
    inputs = content.get("inputs", [])
    inputs_yaml = _list_to_yaml(inputs)

    result = template
    result = result.replace("{{DATE}}", date_str)
    result = result.replace("{{PROJECT_NAME}}", _yaml_safe(project_name))
    result = result.replace("{{TOPIC}}", _yaml_safe(content.get("topic", title)))
    result = result.replace("{{SESSION_ID}}", session_id)
    result = result.replace("inputs: []", f"inputs: {inputs_yaml}")
    result = result.replace("{{VALIDATED_TIMESTAMP}}", ts_str)
    result = result.replace("{{approved / approved_with_edits}}", "approved")

    insights = content.get("insights", [])
    insights_text = "\n".join(f"{i+1}. {ins}" for i, ins in enumerate(insights))
    result = re.sub(
        r"1\. \{\{INSIGHT_1\}\}.*?3\. \{\{INSIGHT_3\}\}",
        insights_text,
        result,
        flags=re.DOTALL,
    )

    result = result.replace("{{CONCEPTUAL_MAP}}", content.get("conceptual_map", ""))

    formulations = content.get("formulations", [])
    form_text = "\n\n".join(f'> "{f}"' for f in formulations) if formulations else '> "(none)"'
    result = re.sub(
        r'> "\{\{FORMULATION_1\}\}".*?> "\{\{FORMULATION_2\}\}"',
        form_text,
        result,
        flags=re.DOTALL,
    )

    questions = content.get("open_questions", [])
    q_text = "\n".join(f"- [ ] {q}" for q in questions) if questions else "- [ ] (none)"
    result = re.sub(
        r"- \[ \] \{\{QUESTION_1\}\}.*?- \[ \] \{\{QUESTION_3\}\}",
        q_text,
        result,
        flags=re.DOTALL,
    )

    result = result.replace("{{CONTEXT_FORWARD}}", content.get("context_forward", ""))

    next_steps = content.get("next_steps", [])
    ns_text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(next_steps)) if next_steps else "1. (TBD)"
    result = re.sub(
        r"1\. \{\{NEXT_STEP_1\}\}.*?2\. \{\{NEXT_STEP_2\}\}",
        ns_text,
        result,
        flags=re.DOTALL,
    )

    result = result.replace("{{WARNINGS}}", content.get("warnings", ""))
    result = result.replace("{{TIMESTAMP}}", ts_str)

    result = result.replace("# Epistemic Trace", f"# Epistemic Trace — {title}")

    return result


def fill_pdl(
    session_id: str,
    project_name: str,
    title: str,
    content: Dict[str, Any],
) -> str:
    """Fill the PDL template."""
    template = load_template("pdl")
    if template is None:
        raise ValueError("pdl_template.md not found in templates/")

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    ts_str = now.strftime("%Y-%m-%dT%H:%M:%S")
    inputs = content.get("inputs", [])
    inputs_yaml = _list_to_yaml(inputs)

    result = template
    result = result.replace("{{PROJECT_NAME}}", _yaml_safe(project_name))
    result = result.replace("{{CREATED_DATE}}", date_str)
    result = result.replace("{{UPDATED_DATE}}", date_str)
    result = result.replace("{{STATUS}}", _yaml_safe(content.get("status", "draft")))
    result = result.replace("{{SESSION_ID}}", session_id)
    result = result.replace("inputs: []", f"inputs: {inputs_yaml}")
    result = result.replace("{{VALIDATED_TIMESTAMP}}", ts_str)
    result = result.replace("{{approved / approved_with_edits}}", "approved")

    entries = content.get("entries", [])
    entries_text = ""
    for e in entries:
        entry_id = e.get("entry_id", "PDL-001")
        options = _normalize_options(e.get("options", []))
        opts_text = ""
        for i, opt in enumerate(options, 1):
            name = opt.get("name", f"Option {i}")
            desc = opt.get("description", "")
            pros = opt.get("pros", "")
            cons = opt.get("cons", "")
            opts_text += f"{i}. **{name}**: {desc}\n"
            if pros:
                opts_text += f"   - Pros: {pros}\n"
            if cons:
                opts_text += f"   - Cons: {cons}\n"
            opts_text += "\n"

        entries_text += f"""### {entry_id}: {e.get('title', '')}

| Field | Value |
|-------|-------|
| Date | {e.get('date', date_str)} |
| Issue/Need | {e.get('issue', '')} |

**Options Considered:**

{opts_text}
**Decision:** {e.get('decision', '')}

**Rationale:** {e.get('rationale', '')}

**What it affects:** {e.get('impact', '')}

---

"""

    result = re.sub(
        r"### PDL-001:.*?(?=## Current Prompt State)",
        entries_text,
        result,
        flags=re.DOTALL,
    )

    result = result.replace("{{CURRENT_PROMPT_SUMMARY}}", content.get("current_state", ""))
    result = result.replace("{{TIMESTAMP}}", ts_str)

    return result


def fill_product_dev_log(
    session_id: str,
    project_name: str,
    title: str,
    content: Dict[str, Any],
) -> str:
    """Fill the Product Development Log template."""
    template = load_template("product_dev_log")
    if template is None:
        raise ValueError("product_dev_log_template.md not found in templates/")

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    ts_str = now.strftime("%Y-%m-%dT%H:%M:%S")
    inputs = content.get("inputs", [])
    inputs_yaml = _list_to_yaml(inputs)

    result = template
    result = result.replace("{{PROJECT_NAME}}", _yaml_safe(project_name))
    result = result.replace("{{CREATED_DATE}}", date_str)
    result = result.replace("{{UPDATED_DATE}}", date_str)
    result = result.replace("{{STATUS}}", _yaml_safe(content.get("status", "draft")))
    result = result.replace("{{SESSION_ID}}", session_id)
    result = result.replace("inputs: []", f"inputs: {inputs_yaml}")
    result = result.replace("{{VALIDATED_TIMESTAMP}}", ts_str)
    result = result.replace("{{approved / approved_with_edits}}", "approved")

    entries = content.get("entries", [])
    entries_text = ""
    for e in entries:
        entry_id = e.get("entry_id", "PDL-001")
        options = _normalize_options(e.get("options", []))
        opts_text = ""
        for i, opt in enumerate(options, 1):
            name = opt.get("name", f"Option {i}")
            desc = opt.get("description", "")
            pros = opt.get("pros", "")
            cons = opt.get("cons", "")
            opts_text += f"{i}. **{name}**: {desc}\n"
            if pros:
                opts_text += f"   - Pros: {pros}\n"
            if cons:
                opts_text += f"   - Cons: {cons}\n"
            opts_text += "\n"

        entries_text += f"""### {entry_id}: {e.get('title', '')}

| Field | Value |
|-------|-------|
| Date | {e.get('date', date_str)} |
| Issue/Need | {e.get('issue', '')} |

**Options Considered:**

{opts_text}
**Decision:** {e.get('decision', '')}

**Rationale:** {e.get('rationale', '')}

**What it affects:** {e.get('impact', '')}

---

"""

    result = re.sub(
        r"### PDL-001:.*?(?=## Current Product State)",
        entries_text,
        result,
        flags=re.DOTALL,
    )

    result = result.replace("{{CURRENT_PRODUCT_SUMMARY}}", content.get("current_state", ""))
    result = result.replace("{{TIMESTAMP}}", ts_str)

    return result


def fill_modlog(
    session_id: str,
    project_name: str,
    title: str,
    content: Dict[str, Any],
) -> str:
    """Fill the modlog template."""
    template = load_template("modlog")
    if template is None:
        raise ValueError("modlog_template.md not found in templates/")

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    ts_str = now.strftime("%Y-%m-%dT%H:%M:%S")
    inputs = content.get("inputs", [])
    inputs_yaml = _list_to_yaml(inputs)

    result = template
    result = result.replace("{{DOCUMENT_NAME}}", _yaml_safe(content.get("document", title)))
    result = result.replace("{{OUTPUT_FILE}}", _yaml_safe(content.get("output_file", "")))
    result = result.replace("{{PROJECT_NAME}}", _yaml_safe(project_name))
    result = result.replace("{{CREATED_DATE}}", date_str)
    result = result.replace("{{UPDATED_DATE}}", date_str)
    result = result.replace("{{SESSION_ID}}", session_id)
    result = result.replace("inputs: []", f"inputs: {inputs_yaml}")
    result = result.replace("{{VALIDATED_TIMESTAMP}}", ts_str)
    result = result.replace("{{approved / approved_with_edits}}", "approved")

    entries = content.get("entries", [])
    if not entries:
        raise ValueError("modlog requires at least one entry in content.entries")

    _REQUIRED_ENTRY_FIELDS = {"entry_id", "type", "change", "rationale"}
    entries_text = ""
    for i, e in enumerate(entries):
        missing = _REQUIRED_ENTRY_FIELDS - set(e.keys())
        if missing:
            raise ValueError(
                f"modlog entry {i} is missing required fields: {sorted(missing)}. "
                f"Expected fields: entry_id, date, type, change, rationale (note is optional). "
                f"Got: {sorted(e.keys())}"
            )

        entry_id = e.get("entry_id", f"MOD-{i+1:03d}")
        note = e.get("note", "")
        note_block = f"\n**Note:**\n{note}\n" if note else ""
        entries_text += f"""### {entry_id}

| Field | Value |
|-------|-------|
| Date | {e.get('date', date_str)} |
| Type | {e.get('type', '')} |

**Change:**
{e.get('change', '')}

**Rationale:**
{e.get('rationale', '')}
{note_block}
---

"""

    result = re.sub(
        r"### MOD-001.*?(?=<!-- ENTRIES_END -->)",
        entries_text,
        result,
        flags=re.DOTALL,
    )

    result = result.replace("{{TIMESTAMP}}", ts_str)

    return result


# ---------------------------------------------------------------------------
# MHC-H additions
# ---------------------------------------------------------------------------

def fill_decision_entry(
    session_id: str,
    project_name: str,
    title: str,
    content: Dict[str, Any],
) -> str:
    """Fill the decision_entry template.

    content fields:
      - topic (str): subject of the decision
      - context (str, optional): situation that prompted it
      - options (list, optional): options considered. Normalized via
        _normalize_options() — accepts list[dict{name,description,pros?,cons?}],
        list[str], str, or dict.
      - decision (str): the choice made
      - rationale (str, optional): why
      - created_at (str, optional): ISO timestamp; defaults to now()
    """
    template = load_template("decision_entry")
    if template is None:
        raise ValueError("decision_entry_template.md not found in templates/")

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    ts_str = content.get("created_at") or now.strftime("%Y-%m-%dT%H:%M:%S")

    options = _normalize_options(content.get("options", []))
    if options:
        opts_text = ""
        for i, opt in enumerate(options, 1):
            name = opt.get("name", f"Option {i}")
            desc = opt.get("description", "")
            pros = opt.get("pros", "")
            cons = opt.get("cons", "")
            opts_text += f"{i}. **{name}**: {desc}\n"
            if pros:
                opts_text += f"   - Pros: {pros}\n"
            if cons:
                opts_text += f"   - Cons: {cons}\n"
            opts_text += "\n"
    else:
        opts_text = "(none considered — direct decision)\n"

    result = template
    result = result.replace("{{PROJECT_NAME}}", _yaml_safe(project_name))
    result = result.replace("{{TITLE}}", _yaml_safe(title))
    result = result.replace("{{TOPIC}}", _yaml_safe(content.get("topic", title)))
    result = result.replace("{{DATE}}", date_str)
    result = result.replace("{{SESSION_ID}}", session_id)
    result = result.replace("{{CREATED_AT}}", ts_str)
    result = result.replace("{{CONTEXT}}", content.get("context", "(not specified)"))
    result = result.replace("{{OPTIONS}}", opts_text)
    result = result.replace("{{DECISION}}", content.get("decision", ""))
    result = result.replace("{{RATIONALE}}", content.get("rationale", "(not specified)"))

    return result


def fill_draft(
    session_id: str,
    project_name: str,
    title: str,
    content: Dict[str, Any],
) -> str:
    """Fill the draft template.

    content fields:
      - draft_type (str, optional): e.g. "memo", "brief", "letter", "spec"
      - content (str): the draft body (markdown)
      - upstream_refs (list[str], optional): artifact_ids cited (decisions,
        traces, etc.) — provenance trail
    """
    template = load_template("draft")
    if template is None:
        raise ValueError("draft_template.md not found in templates/")

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    ts_str = now.strftime("%Y-%m-%dT%H:%M:%S")

    upstream = content.get("upstream_refs", []) or []
    upstream_yaml = _list_to_yaml(upstream)
    upstream_md = (
        "\n".join(f"- {r}" for r in upstream) if upstream else "- (none)"
    )

    result = template
    result = result.replace("{{PROJECT_NAME}}", _yaml_safe(project_name))
    result = result.replace("{{TITLE}}", _yaml_safe(title))
    result = result.replace("{{DRAFT_TYPE}}", _yaml_safe(content.get("draft_type", "memo")))
    result = result.replace("{{DATE}}", date_str)
    result = result.replace("{{SESSION_ID}}", session_id)
    result = result.replace("{{TIMESTAMP}}", ts_str)
    result = result.replace("{{UPSTREAM_REFS_YAML}}", upstream_yaml)
    result = result.replace("{{UPSTREAM_REFS_MD}}", upstream_md)
    result = result.replace("{{CONTENT}}", content.get("content", ""))

    return result


# ---------------------------------------------------------------------------
# Dispatcher (used by /api/artifacts handler)
# ---------------------------------------------------------------------------

FILL_FUNCTIONS = {
    "note": fill_note,
    "trace": fill_trace,
    "pdl": fill_pdl,
    "product_dev_log": fill_product_dev_log,
    "modlog": fill_modlog,
    "decision_entry": fill_decision_entry,
    "draft": fill_draft,
}


def fill_artifact(
    artifact_type: str,
    session_id: str,
    project_name: str,
    title: str,
    content: Dict[str, Any],
) -> str:
    """Return filled artifact markdown for the given type.

    Falls back to a generic substitution for types without a dedicated filler
    (session_log, prompt).
    """
    filler = FILL_FUNCTIONS.get(artifact_type)
    if filler:
        return filler(
            session_id=session_id,
            project_name=project_name,
            title=title,
            content=content,
        )

    template = load_template(artifact_type)
    if template is None:
        raise ValueError(
            f"Unknown artifact_type '{artifact_type}' or template not found in templates/"
        )

    date_str = datetime.now().strftime("%Y-%m-%d")
    result = template
    result = result.replace("[Project name]", project_name)
    result = result.replace("[YYYY-MM-DD]", date_str)
    result = result.replace("[SID-YYYYMMDD-HHMMSS]", session_id)
    result = result.replace("[approved / approved_with_edits]", "approved")
    result = result.replace("{{PROJECT_NAME}}", project_name)
    result = result.replace("{{SESSION_ID}}", session_id)
    return result


__all__ = [
    "TEMPLATE_FILES",
    "load_template",
    "fill_note",
    "fill_trace",
    "fill_pdl",
    "fill_product_dev_log",
    "fill_modlog",
    "fill_decision_entry",
    "fill_draft",
    "fill_artifact",
    "FILL_FUNCTIONS",
]
