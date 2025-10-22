import os, logging, re
from typing import List, Dict, Optional
from jira_live_client import JiraLiveClient

logger = logging.getLogger(__name__)

EXCLUDED_COMPONENTS = {"NGAGE","nGage","Ngage","CPaaS","ECP","LEAP","Leap","LEAP App","LEAP Platform"}
BASE_JQL_NO_ORDER = 'project = "MBSL3"'
ORDER_CLAUSE = ' ORDER BY updated DESC'

ACTIVE_STATUSES = {"Open","In Progress","To Do","In Review","Testing"}
RESOLVED_STATUSES = {"Done","Closed","Resolved"}

def _build_base_jql(include_exclusion: bool = True) -> str:
    """Build base JQL with proper quoting for multi-word component names.

    Jira requires quotes around component names that contain spaces or special characters.
    We quote all components for simplicity/safety.
    """
    if include_exclusion:
        excluded = ','.join(f'"{c}"' for c in sorted(EXCLUDED_COMPONENTS))
        return f"{BASE_JQL_NO_ORDER} AND component NOT IN ({excluded})"
    return BASE_JQL_NO_ORDER

class JiraLiveService:
    def __init__(self):
        url = os.getenv('JIRA_URL') or os.getenv('ATLASSIAN_URL')
        user = os.getenv('JIRA_USERNAME') or os.getenv('ATLASSIAN_USERNAME')
        token = os.getenv('JIRA_API_TOKEN') or os.getenv('ATLASSIAN_API_TOKEN') or os.getenv('JIRA_TOKEN')
        if not all([url,user,token]):
            logger.warning('JiraLiveService missing credentials')
            self.client = None
        else:
            self.client = JiraLiveClient(url,user,token)

    def available(self) -> bool:
        return self.client is not None

    def search(self, jql: str, limit: int = 200) -> List[Dict]:
        if not self.client:
            return []
        return self.client.search_paginated(jql, limit=limit)

    def format_issue(self, issue: Dict) -> Dict:
        f = issue.get('fields', {}) or {}
        return {
            'key': issue.get('key'),
            'summary': f.get('summary',''),
            'status': (f.get('status') or {}).get('name',''),
            'priority': (f.get('priority') or {}).get('name',''),
            'assignee': (f.get('assignee') or {}).get('displayName','Unassigned') if f.get('assignee') else 'Unassigned',
            'reporter': (f.get('reporter') or {}).get('displayName',''),
            'updated': f.get('updated',''),
            'created': f.get('created',''),
            'issueType': (f.get('issuetype') or {}).get('name',''),
            'components': [c.get('name') for c in f.get('components',[])],
        }

    def live_search(self, query: Optional[str], limit: int = 100) -> Dict:
        # Build JQL similar to original, but allow key or text
        if not query:
            jql = _build_base_jql(True) + ORDER_CLAUSE
        elif re.match(r'^[A-Z]+-\d+$', query.upper()):
            jql = f'key = "{query.upper()}"'
        else:
            jql = f'(summary ~ "{query}" OR description ~ "{query}" OR text ~ "{query}") AND ' + _build_base_jql(True) + ORDER_CLAUSE
        raw = self.search(jql, limit=limit)
        formatted = [self.format_issue(i) for i in raw if i.get('key')]
        return {'query': query, 'jql': jql, 'count': len(formatted), 'issues': formatted}

    def summary(self, date_range: str = '30d', limit: int = 400) -> Dict:
        # Basic summary using updated window with fallback if exclusions filter out everything
        use_exclusion = True
        def build_jql(include_ex):
            base = _build_base_jql(include_ex)
            if date_range.endswith('d'):
                return base + f' AND updated >= -{date_range}' + ORDER_CLAUSE
            return base + ORDER_CLAUSE
        jql_primary = build_jql(True)
        try:
            issues = self.search(jql_primary, limit=limit)
        except Exception as e:
            logger.warning(f"Primary summary search failed, retrying without exclusions: {e}")
            issues = []
        if not issues:  # fallback path
            jql_fallback = build_jql(False)
            fallback = self.search(jql_fallback, limit=limit)
            if fallback:
                logger.info(f"Summary fallback used (primary zero). Primary JQL: {jql_primary} | Fallback JQL: {jql_fallback} -> {len(fallback)} issues")
                issues = fallback
                use_exclusion = False
        formatted = [self.format_issue(i) for i in issues if i.get('key')]
        total = len(formatted)
        status_counts = {}
        assignees = {}
        priorities = {}
        active = resolved = 0
        for t in formatted:
            s = t['status'] or 'Unknown'
            status_counts[s] = status_counts.get(s,0)+1
            if s in ACTIVE_STATUSES: active += 1
            if s in RESOLVED_STATUSES: resolved += 1
            a = t['assignee'] or 'Unassigned'
            assignees[a] = assignees.get(a,0)+1
            p = t['priority'] or 'Unknown'
            priorities[p] = priorities.get(p,0)+1
        return {
            'total': total,
            'active': active,
            'resolved': resolved,
            'active_pct': round(active/total*100,1) if total else 0,
            'resolved_pct': round(resolved/total*100,1) if total else 0,
            'status_distribution': status_counts,
            'priority_distribution': priorities,
            'assignee_top': sorted(assignees.items(), key=lambda x: x[1], reverse=True)[:15],
            'used_exclusion': use_exclusion
        }

    def team_analytics(self, limit: int = 400) -> Dict:
        jql = _build_base_jql(True) + ORDER_CLAUSE
        issues = self.search(jql, limit=limit)
        formatted = [self.format_issue(i) for i in issues if i.get('key')]
        per_assignee = {}
        for t in formatted:
            a = t['assignee'] or 'Unassigned'
            entry = per_assignee.setdefault(a, {'done':0,'progress':0,'todo':0,'total':0})
            st = t['status']
            if st in RESOLVED_STATUSES: entry['done'] += 1
            elif st in ACTIVE_STATUSES: entry['progress'] += 1
            else: entry['todo'] += 1
            entry['total'] += 1
        cards = []
        for assignee, data in per_assignee.items():
            completion = round(data['done']/data['total']*100,1) if data['total'] else 0
            cards.append({'assignee': assignee, 'done': data['done'], 'progress': data['progress'], 'todo': data['todo'], 'completion_pct': completion})
        cards.sort(key=lambda x: x['completion_pct'], reverse=True)
        return {'team_members': len(per_assignee), 'cards': cards[:30]}
