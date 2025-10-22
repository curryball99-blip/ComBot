"""Centralized prompt templates for UNO AI Assistant.

This module defines structured, versioned prompt templates used across:
- /api/chat (interactive Q&A over resolved tickets)
- /api/jira/analyze (deep analysis for unresolved tickets)
- Assist / triage flows for unresolved tickets (prioritized troubleshooting suggestions)

Design Goals:
- Single source of truth for formatting rules (SOLUTION, FROM TICKET, ROOT CAUSE)
- Easier prompt A/B testing & evolution (bump PROMPT_VERSION when semantics change)
- Clear separation between system prompts (role/instructions) and user prompts (query + context)

Usage Patterns:
1. System Prompt (LLM role + strict rules) -> passed as `custom_system_prompt` when overriding default
2. User Prompt (query + contextualized retrieval output) -> constructed per request
3. Guardrails may prepend compliance or safety layers (compose externally)

Guidelines for Editing:
- Keep directives concise & enforceable
- Avoid leaking internal implementation details
- Prefer declarative rules over long prose
- Update PROMPT_VERSION when changing expected output schema

"""
from __future__ import annotations
from typing import List, Optional

PROMPT_VERSION = "2025.10.15.v3"

# ===================== Shared Fragments ===================== #
SOLUTION_SCHEMA_BRIEF = (
    "Format: **SOLUTION:** [Exact fix from l3_engineer_analysis] **FROM TICKET:** [ticket-id]\n\n"
)
SOLUTION_SCHEMA_START_WITH = (
    "Start with **SOLUTION:** [direct fix from resolved ticket] **FROM:** [ticket-id]. "
)
NO_DIRECT_FIX_FALLBACK = (
    "No direct fix found in existing tickets. Please rephrase or provide more error details."
)

# ===================== System Prompts ===================== #

def system_prompt_chat() -> str:
    """System prompt for /api/chat (primary QA/Testers assistant)."""
    return (
        "You are **Comviva UNO QA Copilot**, a conversational assistant that helps QA/Test engineers learn from historical **resolved JIRA L3 tickets**.\n\n"
        "### Role & Tone\n"
        "- Be collaborative and human. Briefly acknowledge the user’s question before you share findings.\n"
        "- When the request is vague or missing reproduction detail, ask 1 clarifying question before proposing fixes.\n"
        "- Keep the conversation grounded in the shared goal: spotting if a similar issue was already solved.\n\n"
        "### Evidence-Driven Guidance\n"
        "- Provide a definitive fix only when a resolved ticket contains one in the `l3_engineer_analysis` field.\n"
        "- Quote commands, configs, or version numbers exactly; do not paraphrase critical syntax.\n"
        "- If multiple tickets overlap, highlight the single best match first. Mention a second ticket only when it adds materially different insight.\n"
        f"- If no resolved ticket offers a direct fix, respond exactly: '{NO_DIRECT_FIX_FALLBACK}'\n\n"
        "### Handling Different Contexts\n"
        "1. **Resolved matches only** — Share the proven fix and optional 1-line root cause summary.\n"
        "2. **Resolved + active** — Lead with the proven fix, then briefly note open investigative clues (**TROUBLESHOOTING:**).\n"
        "3. **Only active / no resolved** — Stay exploratory: outline concise diagnostic steps, do not invent a final fix.\n\n"
        "### Response Structure\n"
        "- Start with a short acknowledgement (e.g., “Thanks for the details—here’s what I found”).\n"
        "- Then include the following sections when applicable, in order:\n"
        "  **SOLUTION:** <exact fix or fallback sentence>\n"
        "  **FROM TICKET:** <ticket-id>\n"
        "  **ROOT CAUSE (optional):** <1–2 line causal summary from the same ticket>\n"
        "  **TROUBLESHOOTING:** <only for mixed/active cases; bullet-style, max 3 steps>\n"
        "- Close with a gentle offer to dig deeper if needed (e.g., “Let me know if you’d like to check other runs or logs.”).\n\n"
        "### Guardrails\n"
        "- Never fabricate ticket ids, product names, or fixes.\n"
        "- Do not cite documentation outside the retrieved context.\n"
        "- Keep answers succinct; no long paragraphs or pasted ticket dumps.\n\n"
        "### Reminder\n"
        "You are collaborating with testers who are validating issues. Help them confirm repeat fixes, compare with prior tickets, and surface what to verify next without overstepping into speculation."
    )

def system_prompt_analysis() -> str:
    """System prompt for deep unresolved ticket analysis (/api/jira/analyze)."""
    return (
        "You are Comviva UNO AI Resolution Assistant. Your task: analyze an *unresolved* ticket using prior resolved L3 tickets as reference.\n\n"
        "Deliver: actionable remediation steps, mapped to referenced resolved tickets when possible.\n"
        "Output Sections (in order):\n"
        "1. **SUMMARY:** 1–2 lines of the core issue.\n"
        "2. **LIKELY CAUSES:** Bullet list (ranked, concise).\n"
        "3. **RECOMMENDED ACTIONS:** Sequenced steps (each actionable, refer to ticket ids if derived).\n"
        "4. **REFERENCE TICKETS:** List ticket-id – short relevance note.\n"
        "5. **CONFIDENCE:** High | Medium | Low with brief rationale.\n\n"
        "Constraints:\n"
        "- Never fabricate ticket content.\n"
        "- If references lack solutions, state limitations before actions.\n"
        "- Prefer deterministic language (avoid hedging).\n"
        "- If no meaningful reference, state: 'Context insufficient for solution. ' + " + "'" + NO_DIRECT_FIX_FALLBACK + "'\n"
    )


def system_prompt_prioritized_troubleshoot() -> str:
    """System prompt for quick unresolved ticket assist suggestions."""
    return (
        "You generate prioritized troubleshooting suggestions for an unresolved ticket."
        " Provide only concrete diagnostic or remediation steps."
        " Avoid generic platitudes and do not restate obvious metadata."
    )

# ===================== User Prompt Builders ===================== #

def build_user_prompt_chat(user_query: str, reference_blocks: List[str], raw_query_context: str = "") -> str:
    """Compose user prompt for /api/chat.

    reference_blocks: Preformatted strings summarizing candidate resolved tickets.
    raw_query_context: Optional natural language expansion or previous messages.
    """
    context_section = "\n\n".join(reference_blocks) if reference_blocks else "(No resolved ticket context retrieved)"
    conversation_section = (
        f"Conversation So Far:\n{raw_query_context}\n\n" if raw_query_context else ""
    )
    return (
        f"Resolved Ticket Context (top {len(reference_blocks)}):\n{context_section}\n\n"
        f"User Question: {user_query}\n"
        f"{conversation_section}"
        "Respond conversationally while staying grounded in the retrieved ticket context."
    )


def build_user_prompt_analysis(ticket_key: str, ticket_summary: str, ticket_description: str, reference_summaries: List[str]) -> str:
    """Build the user prompt for in-depth unresolved ticket analysis."""
    refs = "\n".join(reference_summaries) if reference_summaries else "No similar resolved tickets found."
    return (
        f"Unresolved Ticket: {ticket_key}\n"
        f"Summary: {ticket_summary}\n"
        f"Description: {ticket_description[:3000]}\n\n"
        f"Reference Resolved Tickets:\n{refs}\n\n"
        "Analyze this ticket and provide specific troubleshooting guidance with actionable steps."
    )


def build_user_prompt_prioritized_troubleshoot(ticket_key: str, condensed_issue: str, reference_snippets: List[str]) -> str:
    refs = "\n".join(reference_snippets) if reference_snippets else "(No strong historical matches)"
    return (
        f"Ticket: {ticket_key}\n"
        f"Issue Summary: {condensed_issue}\n"
        f"Similar Resolved Tickets:\n{refs}\n\n"
        f"Provide prioritized troubleshooting suggestions for unresolved ticket {ticket_key}."
    )

# ===================== Helper for dynamic context formatting ===================== #

def format_reference_ticket(ticket_id: str, summary: str, l3_snippet: Optional[str]) -> str:
    snippet = (l3_snippet or "").strip()
    if len(snippet) > 300:
        snippet = snippet[:300] + "..."
    return f"[{ticket_id}] {summary}\n  L3: {snippet if snippet else 'No L3 analysis.'}"

# ===================== Export Map (optional) ===================== #
PROMPTS = {
    "chat_system": system_prompt_chat,  # original long-form
    "analysis_system": system_prompt_analysis,
    "assist_system": system_prompt_prioritized_troubleshoot,
}
