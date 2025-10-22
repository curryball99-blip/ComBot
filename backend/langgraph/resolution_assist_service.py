"""
Resolution Assist Service (Tier 1)
=================================

Provides semantic retrieval over resolved tickets plus structured fallback guidance.
Non-intrusive: does not modify existing JiraAssistResponse schema or current ingestion logic.

Phases Implemented:
- Semantic retrieval placeholder (currently uses scroll + lexical overlap; ready for embedding upgrade)
- Fallback template when no references meet threshold
- Synthesis prompt assembly (delegates to Groq client injected externally)

Future Enhancements (not implemented yet):
- True vector search using JiraQdrantService search_all_tickets with filters
- Distilled resolution fields (root_cause, fix_steps, etc.)
- Heuristic re-ranking & confidence scoring

Usage:
    service = ResolutionAssistService(jira_service, qdrant_base_url, ingestion_version)
    result = await service.assist(ticket_key, groq_client, max_refs=5)

Result schema matches JiraAssistResponse fields.
Tier 2 Additions (Semantic Retrieval):
 - If embedding & qdrant services provided, perform vector similarity search over resolved tickets.
 - Filter: is_resolved=True & ingestion_version match.
 - Heuristic re-rank using label/component overlap.
 - Preserve original lexical path as fallback.
"""
from __future__ import annotations
import os
import logging
from typing import List, Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)

# Debug storage for last assist call
_LAST_ASSIST_DEBUG: Dict[str, Any] = {}

class ResolutionAssistService:
    def __init__(
        self,
        jira_service,
        ingestion_version: str,
        embedding_service: Optional[object] = None,
        qdrant_service: Optional[object] = None,
    ):
        self.jira_service = jira_service
        self.ingestion_version = ingestion_version
        self.qdrant_url = os.getenv('QDRANT_URL', 'http://localhost:6333')
        self.embedding_service = embedding_service
        self.qdrant_service = qdrant_service
        # Lexical heuristic threshold (overlap count)
        self.min_overlap = 2
        # Semantic similarity threshold (cosine) for acceptance
        self.semantic_threshold = float(os.getenv('ASSIST_SEMANTIC_THRESHOLD', '0.34'))
        # Enable semantic only if both services present
        self.semantic_enabled = bool(self.embedding_service and self.qdrant_service)

    async def assist(self, ticket_key: str, groq_client, max_refs: int = 5) -> Dict[str, Any]:
        """Generate assist suggestion for an unresolved ticket.
        Returns dict with keys matching JiraAssistResponse.
        """
        details = await self.jira_service.get_ticket_details(ticket_key)
        if not details:
            raise ValueError("Ticket not found")
        status = (details.get('status') or '').title()
        resolved_statuses = {"Done","Closed","Resolved"}
        if status in resolved_statuses:
            suggestion = await self._summarize_resolved(ticket_key, details, groq_client)
            return {
                'ticket_key': ticket_key,
                'status': status,
                'resolved_reference_count': 0,
                'references': [],
                'suggestion': suggestion
            }
        # unresolved path
        retrieval_method = "semantic" if self.semantic_enabled else "lexical"
        if self.semantic_enabled:
            refs = await self._retrieve_resolved_references_semantic(details, max_refs)
            if not refs:
                logger.info("Semantic retrieval returned no matches above threshold; falling back to lexical heuristic")
                retrieval_method = "lexical_fallback"
                refs = await self._retrieve_resolved_references_lexical(details, max_refs)
        else:
            refs = await self._retrieve_resolved_references_lexical(details, max_refs)
        # Store debug info
        try:
            _LAST_ASSIST_DEBUG.update({
                'ticket_key': ticket_key,
                'status': status,
                'semantic_enabled': self.semantic_enabled,
                'retrieval_method': retrieval_method,
                'reference_count': len(refs),
                'references_preview': [r.get('ticket_key') for r in refs[:10]],
                'similarity_scores': [r.get('similarity_score') for r in refs if 'similarity_score' in r],
            })
        except Exception:
            pass
        suggestion = await self._generate_guidance(ticket_key, details, refs, groq_client)
        return {
            'ticket_key': ticket_key,
            'status': status,
            'resolved_reference_count': len(refs),
            'references': refs,
            'suggestion': suggestion
        }

    async def _summarize_resolved(self, ticket_key: str, details: Dict[str, Any], groq_client) -> str:
        prompt = f"Provide a concise resolution summary for resolved ticket {ticket_key}. Include key fix actions."
        return await groq_client.generate_response_async(
            query=prompt,
            context=f"Summary: {details.get('summary','')}\nDescription: {details.get('description','')[:1500]}",
            temperature=0.3,
            max_tokens=400,
            top_p=0.9,
            model=os.getenv('LLM_MODEL', 'llama-3.3-70b-versatile'),
            use_custom_prompt=True,
            custom_system_prompt="You summarize already-resolved JIRA tickets precisely without proposing new steps."
        )

    async def _retrieve_resolved_references_lexical(self, details: Dict[str, Any], max_refs: int) -> List[Dict[str, Any]]:
        """Existing scroll + lexical overlap heuristic."""
        refs: List[Dict[str, Any]] = []
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                body = {
                    "limit": 300,
                    "with_payload": True,
                    "filter": {"must": [
                        {"key": "is_resolved", "match": {"value": True}},
                        {"key": "ingestion_version", "match": {"value": self.ingestion_version}}
                    ]}
                }
                resp = await client.post(f"{self.qdrant_url}/collections/jira_tickets/points/scroll", json=body)
                if resp.status_code == 200:
                    points = resp.json().get('result', {}).get('points', [])
                    target_words = set(details.get('summary','').lower().split())
                    scored = []
                    for p in points:
                        pl = p.get('payload', {})
                        summary = (pl.get('summary') or '').lower()
                        overlap = len(target_words & set(summary.split()))
                        if overlap >= self.min_overlap:
                            scored.append((overlap, pl))
                    scored.sort(key=lambda x: x[0], reverse=True)
                    for overlap, pl in scored[:max_refs]:
                        refs.append({
                            'ticket_key': pl.get('ticket_key'),
                            'status': pl.get('status'),
                            'summary': pl.get('summary'),
                            'l1_l2_analysis': pl.get('l1_l2_analysis'),
                            'l3_engineer_analysis': pl.get('l3_engineer_analysis'),
                            'overlap': overlap
                        })
        except Exception as e:
            logger.warning(f"ResolutionAssistService lexical retrieval failed: {e}")
        return refs

    async def _retrieve_resolved_references_semantic(self, details: Dict[str, Any], max_refs: int) -> List[Dict[str, Any]]:
        """Semantic vector search using embedding & Qdrant services.
        Returns list of reference dicts aligned with lexical format plus similarity metadata.
        """
        if not self.semantic_enabled:
            return []
        try:
            summary = details.get('summary', '') or ''
            description = (details.get('description') or '')[:1500]
            query_text = f"{summary}\n{description}".strip()
            # Generate embedding
            vector = self.embedding_service.get_embedding(query_text)  # synchronous call
            # Perform search with filters
            filters = {"is_resolved": True, "ingestion_version": self.ingestion_version}
            results = await self.qdrant_service.search_all_tickets(
                query_vector=vector,
                limit=max_refs * 3,  # over-fetch for re-rank
                score_threshold=self.semantic_threshold,
                filters=filters
            )
            if not results:
                return []
            # Heuristic re-rank boost
            target_labels = set((details.get('labels') or []) or [])
            target_components = set((details.get('components') or []) or [])
            enriched = []
            for r in results:
                pl = r.get('payload', {})
                labels = set(pl.get('labels') or [])
                components = set(pl.get('components') or [])
                label_overlap = len(labels & target_labels)
                component_overlap = len(components & target_components)
                base_score = r.get('score', 0.0)
                adjusted = base_score * (1 + 0.05 * label_overlap + 0.07 * component_overlap)
                enriched.append({
                    'payload': pl,
                    'score': base_score,
                    'adjusted_score': adjusted,
                    'label_overlap': label_overlap,
                    'component_overlap': component_overlap
                })
            enriched.sort(key=lambda x: x['adjusted_score'], reverse=True)
            refs: List[Dict[str, Any]] = []
            for item in enriched[:max_refs]:
                pl = item['payload']
                # Provide pseudo-overlap integer for backward UI compatibility (scaled)
                pseudo_overlap = int(round(item['adjusted_score'] * 100))
                refs.append({
                    'ticket_key': pl.get('ticket_key'),
                    'status': pl.get('status'),
                    'summary': pl.get('summary'),
                    'l1_l2_analysis': pl.get('l1_l2_analysis'),
                    'l3_engineer_analysis': pl.get('l3_engineer_analysis'),
                    'overlap': pseudo_overlap,
                    'similarity_score': item['score'],
                    'adjusted_score': item['adjusted_score']
                })
            return refs
        except Exception as e:
            logger.warning(f"Semantic retrieval failed: {e}")
            return []

    async def _generate_guidance(self, ticket_key: str, details: Dict[str, Any], refs: List[Dict[str, Any]], groq_client) -> str:
        if not refs:
            return self._generic_fallback(details)
        reference_context = []
        for r in refs:
            reference_context.append(
                f"Ref {r['ticket_key']} (Status {r['status']}): {r.get('summary','')}. L1/L2: {(r.get('l1_l2_analysis') or '')[:250]} L3: {(r.get('l3_engineer_analysis') or '')[:250]}"
            )
        ref_block = "\n".join(reference_context)[:6000]
        system_prompt = (
            "You generate guidance for unresolved JIRA tickets using ONLY the referenced resolved tickets. "
            "Never fabricate steps; if context insufficient, ask for specific missing logs or metrics."
        )
        return await groq_client.generate_response_async(
            query=f"Provide prioritized troubleshooting suggestions for unresolved ticket {ticket_key}.",
            context=f"Unresolved Ticket Summary: {details.get('summary','')}\nDescription: {details.get('description','')[:1500]}\n\nResolved References:\n{ref_block}",
            temperature=0.4,
            max_tokens=600,
            top_p=0.9,
            model=os.getenv('LLM_MODEL', 'llama-3.3-70b-versatile'),
            use_custom_prompt=True,
            custom_system_prompt=system_prompt
        )

    def _generic_fallback(self, details: Dict[str, Any]) -> str:
        summary = details.get('summary','')
        return (
            "No sufficiently similar resolved tickets were found. "
            "Follow a structured diagnostic path:\n"
            f"1. Clarify Scope: Confirm exact failure for '{summary}'.\n"
            "2. Reproduce: Minimal reproducible steps & environment parity.\n"
            "3. Logs & Metrics: Collect error stack traces, latency spikes, resource usage.\n"
            "4. Configuration: Compare against last known good version, recent changes.\n"
            "5. Dependencies: Check service integrations, API timeouts, version drift.\n"
            "6. Narrow Root Cause: Binary search components; enable targeted debug logging.\n"
            "7. Mitigation: Provide temporary workaround (rate limit, restart component) if user impact high.\n"
            "8. Verification: Define success signals before applying permanent fix.\n"
            "9. Prevention: Plan observability or guardrail to catch recurrence earlier."
        )


def get_last_assist_debug() -> Dict[str, Any]:
    """Accessor for last assist debug info."""
    return dict(_LAST_ASSIST_DEBUG) if _LAST_ASSIST_DEBUG else {}
