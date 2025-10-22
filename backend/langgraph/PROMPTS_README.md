# Prompt Templates (UNO AI Assistant)

Centralized prompt management lives in `prompt_templates.py`.

## Goals
- **Single source of truth** for system & user prompts
- **Clear separation** between use-cases:
  - Chat over resolved tickets (`/api/chat`)
  - Unresolved ticket deep analysis (`/api/jira/analyze`)
  - Quick prioritized assist (`/api/jira/assist/{ticket_key}`)
- **Versioning** via `PROMPT_VERSION`
- **Safer edits** without touching large endpoint file `app_langgraph.py`

## Structure
| Category | Function / Constant | Purpose |
|----------|---------------------|---------|
| System | `system_prompt_chat()` | Role + rules for resolved ticket Q&A |
| System | `system_prompt_analysis()` | Structured deep analysis sections |
| System | `system_prompt_prioritized_troubleshoot()` | Lightweight unresolved assist |
| User | `build_user_prompt_chat()` | Compiles retrieved ticket snippets + query |
| User | `build_user_prompt_analysis()` | Includes unresolved ticket + similar references |
| User | `build_user_prompt_prioritized_troubleshoot()` | Focused suggestions prompt |
| Fragments | `SOLUTION_SCHEMA_BRIEF`, `SOLUTION_SCHEMA_START_WITH` | Reusable formatting strings |
| Helpers | `format_reference_ticket()` | Consistent reference snippet formatting |

## Editing Guidelines
1. Keep **system prompts** stable; avoid frequent churn (affects output style).
2. If you change output schema (e.g., rename sections), **bump `PROMPT_VERSION`**.
3. Never hard-code new prompts inside `app_langgraph.py`—add here and import.
4. When adding a new mode:
   - Add a system prompt builder
   - Optionally add a user prompt builder
   - Update `groq_client_async.AsyncGroqClient` mode switch logic
5. Avoid embedding transient experiment text; instead add a parameter flag or A/B block.

## Mode Routing
`groq_client_async` now accepts `mode` in `{chat, analyze, assist}` to auto-select a system prompt unless a `custom_system_prompt` override is explicitly supplied.

## Custom Prompts
Clients can still pass `use_custom_prompt=True` with `custom_system_prompt=...` to override any system prompt (guardrails from endpoints may prepend additional constraints).

## Future Ideas
- Add YAML-driven prompt registry for hot reload without deploy.
- Maintain prompt performance telemetry keyed by `PROMPT_VERSION`.
- Add test harness comparing output diff before/after prompt changes.

## Safe Change Checklist
- [ ] Updated `PROMPT_VERSION` if structural change
- [ ] Ran `/api/chat` smoke test
- [ ] Ran `/api/jira/assist/{key}` with unresolved ticket
- [ ] Ran `/api/jira/analyze` with sample unresolved ticket
- [ ] Verified no NameError / import error in logs

---
Questions? Edit carefully, commit, and monitor initial responses for drift.
