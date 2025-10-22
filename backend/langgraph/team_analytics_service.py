import statistics
from collections import Counter
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
from .jira_service import JQL_QUERY

logger = logging.getLogger(__name__)

RESOLVED_STATUSES = {s.lower() for s in ['Done','Closed','Resolved']}
ACTIVE_STATUSES = {s.lower() for s in ['In Progress','Testing','Review','QA','Test']}
TODO_STATUSES = {s.lower() for s in ['To Do','Open','Backlog','Selected for Development']}
HIGH_PRIORITY_LEVELS = {p.lower() for p in ['Highest', 'High', 'Critical', 'Blocker']}

class TeamAnalyticsService:
    """Derive lightweight productivity / performance metrics from JIRA tickets.

    Assumes jira_service exposes async method search_tickets(custom_jql=..., max_results=...).
    Returned ticket dicts should include at least:
      key, summary, status, assignee, priority, issueType, created (ISO), updated (ISO), resolutionDate (optional)
    """

    def __init__(self, jira_service):
        self.jira = jira_service

    # ---------------- Public APIs ---------------- #
    async def get_team_analytics(self, date_range: str = '30d', custom_jql: Optional[str] = None, max_results: int = 2000) -> Dict[str, Any]:
        days = self._parse_range_days(date_range)
        now = datetime.utcnow()
        since = now - timedelta(days=days)

        if custom_jql and custom_jql.strip():
            base_jql = custom_jql.strip()
            if 'ORDER BY' not in base_jql.upper():
                base_jql += ' ORDER BY updated DESC'
            jql = base_jql
        else:
            # Use default scoped JQL from JiraService to avoid pulling tickets from unrelated projects/components
            base = JQL_QUERY
            # Remove any ORDER BY clause from the base so we can append our date filter and ordering
            if 'ORDER BY' in base.upper():
                base = base.rsplit('ORDER BY', 1)[0].strip()
            jql = f'{base} AND updated >= "{since.strftime("%Y-%m-%d")}" ORDER BY updated DESC'

        try:
            tickets = await self.jira.search_tickets(custom_jql=jql, max_results=max_results)
        except Exception as e:
            logger.error(f"TeamAnalyticsService JQL search failed: {e}")
            return {"error": "jira_search_failed", "detail": str(e)}

        norm: List[Dict[str, Any]] = []
        for t in tickets:
            if not isinstance(t, dict):
                continue
            assignee = t.get('assignee') or 'Unassigned'
            status = (t.get('status') or '').strip()
            created = self._parse_dt(t.get('created'))
            updated = self._parse_dt(t.get('updated'))
            resolved = self._parse_dt(t.get('resolutionDate'))
            norm.append({
                'key': t.get('key'),
                'assignee': assignee,
                'status': status,
                'priority': (t.get('priority') or 'Unprioritized') or 'Unprioritized',
                'issue_type': (t.get('issueType') or 'Unspecified') or 'Unspecified',
                'created': created,
                'updated': updated,
                'resolved': resolved
            })

        status_counts: Counter = Counter()
        priority_counts: Counter = Counter()
        type_counts: Counter = Counter()
        daily_created: Counter = Counter()
        daily_resolved: Counter = Counter()
        backlog_todo = 0
        backlog_active = 0
        open_high_priority = 0
        aging_backlog = 0
        stalled_in_progress = 0

        for t in norm:
            status_value = (t.get('status') or 'Unknown').strip() or 'Unknown'
            priority_value = (t.get('priority') or 'Unprioritized').strip() or 'Unprioritized'
            issue_type_value = (t.get('issue_type') or 'Unspecified').strip() or 'Unspecified'

            status_counts[status_value] += 1
            priority_counts[priority_value] += 1
            type_counts[issue_type_value] += 1

            if t.get('created'):
                created_day = t['created'].date()
                daily_created[created_day] += 1
            if t.get('resolved'):
                resolved_day = t['resolved'].date()
                daily_resolved[resolved_day] += 1

            status_lower = status_value.lower()
            priority_lower = priority_value.lower()
            last_touch = t.get('updated') or t.get('created')

            if status_lower in TODO_STATUSES:
                backlog_todo += 1
                if t.get('created') and (now - t['created']).days > 14:
                    aging_backlog += 1
            if status_lower in ACTIVE_STATUSES:
                backlog_active += 1
                if last_touch and (now - last_touch).days >= 7:
                    stalled_in_progress += 1
            if status_lower not in RESOLVED_STATUSES and priority_lower in HIGH_PRIORITY_LEVELS:
                open_high_priority += 1

        by_user: Dict[str, List[Dict[str, Any]]] = {}
        for t in norm:
            by_user.setdefault(t['assignee'], []).append(t)

        individual_metrics: List[Dict[str, Any]] = []
        resolution_times: List[float] = []

        for user, items in by_user.items():
            done = sum(1 for i in items if (i['status'] or '').lower() in RESOLVED_STATUSES)
            in_progress = sum(1 for i in items if (i['status'] or '').lower() in ACTIVE_STATUSES)
            todo = sum(1 for i in items if (i['status'] or '').lower() in TODO_STATUSES)
            total = done + in_progress + todo
            completion_rate = (done / total) * 100 if total else 0

            for i in items:
                if i['resolved'] and i['created']:
                    delta = (i['resolved'] - i['created']).total_seconds() / 86400.0
                    if delta >= 0:
                        resolution_times.append(delta)

            score = self._compute_score(done, in_progress, todo, completion_rate)

            individual_metrics.append({
                'assignee': user,
                'done': done,
                'progress': in_progress,
                'todo': todo,
                'total': total,
                'completion_rate': round(completion_rate, 2),
                'score': score
            })

        active_contributors = [m for m in individual_metrics if m['total'] > 0]
        try:
            avg_completion = round(statistics.mean([m['completion_rate'] for m in active_contributors]), 2) if active_contributors else 0
        except statistics.StatisticsError:
            avg_completion = 0
        try:
            avg_resolution_days = round(statistics.mean(resolution_times), 2) if resolution_times else 0.0
        except statistics.StatisticsError:
            avg_resolution_days = 0.0

        individual_metrics.sort(key=lambda x: (-x['score'], x['assignee'].lower()))

        team_done = sum(m['done'] for m in individual_metrics)
        team_progress = sum(m['progress'] for m in individual_metrics)
        team_todo = sum(m['todo'] for m in individual_metrics)

        observation_days = max((now.date() - since.date()).days + 1, 1)
        total_created = sum(daily_created.values())
        total_resolved = sum(daily_resolved.values())
        avg_created_per_day = round(total_created / observation_days, 2) if total_created else 0.0
        avg_resolved_per_day = round(total_resolved / observation_days, 2) if total_resolved else 0.0

        created_last_7 = sum(daily_created.get((now.date() - timedelta(days=i)), 0) for i in range(min(7, observation_days)))
        resolved_last_7 = sum(daily_resolved.get((now.date() - timedelta(days=i)), 0) for i in range(min(7, observation_days)))

        projected_new_tickets = int(round(avg_created_per_day * 7)) if avg_created_per_day else created_last_7
        projected_completed_tickets = int(round(avg_resolved_per_day * 7)) if avg_resolved_per_day else resolved_last_7
        backlog_delta_projection = projected_new_tickets - projected_completed_tickets

        backlog_trend = 'stable'
        if backlog_delta_projection > 3:
            backlog_trend = 'increasing'
        elif backlog_delta_projection < -3:
            backlog_trend = 'decreasing'

        effective_resolution_days = avg_resolution_days if avg_resolution_days else (statistics.mean(resolution_times) if resolution_times else 1.0)
        estimated_effort_hours = round(projected_new_tickets * max(effective_resolution_days, 0.5) * 6, 1)

        confidence = 'low'
        if len(norm) >= 75:
            confidence = 'high'
        elif len(norm) >= 25:
            confidence = 'medium'

        forecast_notes: List[str] = []
        if len(norm) < 10:
            forecast_notes.append('Limited sample size, forecast may fluctuate.')
        if backlog_trend == 'increasing':
            forecast_notes.append('Backlog is trending up — consider shifting capacity to triage new tickets.')
        elif backlog_trend == 'decreasing':
            forecast_notes.append('Team is burning down work faster than new tickets are arriving.')
        else:
            forecast_notes.append('Created and completed work are roughly balanced.')
        if open_high_priority:
            forecast_notes.append(f'{open_high_priority} high-priority items remain open; keep focus on critical issues.')

        daily_throughput = []
        lookback = min(days, 14, observation_days)
        for i in range(lookback - 1, -1, -1):
            day = now.date() - timedelta(days=i)
            daily_throughput.append({
                'date': day.isoformat(),
                'created': daily_created.get(day, 0),
                'resolved': daily_resolved.get(day, 0)
            })

        def _ordered(counter: Counter) -> Dict[str, int]:
            return {k: counter[k] for k in sorted(counter, key=lambda x: (-counter[x], x.lower()))}

        risk_alerts: List[Dict[str, Any]] = []
        if open_high_priority >= 10:
            risk_alerts.append({
                'severity': 'critical',
                'title': 'High-priority backlog spike',
                'message': f'{open_high_priority} critical tickets are still unresolved.',
                'metric': 'open_high_priority',
                'value': open_high_priority
            })
        elif open_high_priority >= 3:
            risk_alerts.append({
                'severity': 'warning',
                'title': 'High-priority backlog',
                'message': f'{open_high_priority} high-priority tickets pending attention.',
                'metric': 'open_high_priority',
                'value': open_high_priority
            })

        if aging_backlog >= 15:
            risk_alerts.append({
                'severity': 'warning',
                'title': 'Aging backlog',
                'message': f'{aging_backlog} tickets have been waiting over two weeks.',
                'metric': 'aging_backlog',
                'value': aging_backlog
            })

        if stalled_in_progress >= 8:
            risk_alerts.append({
                'severity': 'info',
                'title': 'Stalled in progress',
                'message': f'{stalled_in_progress} in-progress tickets have had no movement in 7+ days.',
                'metric': 'stalled_in_progress',
                'value': stalled_in_progress
            })

        if avg_completion < 55 and len(active_contributors) >= 3:
            risk_alerts.append({
                'severity': 'info',
                'title': 'Completion rate dip',
                'message': 'Overall completion rate fell below 55%. Consider reviewing blockers.',
                'metric': 'avg_completion_rate',
                'value': avg_completion
            })

        trend_metrics = {
            'observation_window_days': observation_days,
            'avg_created_per_day': avg_created_per_day,
            'avg_resolved_per_day': avg_resolved_per_day,
            'created_last_7_days': created_last_7,
            'resolved_last_7_days': resolved_last_7,
            'throughput_ratio': round(avg_resolved_per_day / avg_created_per_day, 2) if avg_created_per_day else None,
            'daily_throughput': daily_throughput
        }

        forecast = {
            'projected_new_tickets': projected_new_tickets,
            'projected_completed_tickets': projected_completed_tickets,
            'backlog_delta_next_7_days': backlog_delta_projection,
            'backlog_trend': backlog_trend,
            'estimated_effort_hours': estimated_effort_hours,
            'confidence': confidence,
            'notes': forecast_notes
        }

        team_overview = {
            'status_distribution': _ordered(status_counts),
            'priority_distribution': _ordered(priority_counts),
            'type_distribution': _ordered(type_counts)
        }

        return {
            'range_days': days,
            'team_summary': {
                'team_members': len(active_contributors),
                'total_tickets': len(norm),
                'avg_completion_rate': avg_completion,
                'avg_resolution_days': avg_resolution_days,
                'done': team_done,
                'in_progress': team_progress,
                'todo': team_todo,
                'open_high_priority': open_high_priority,
                'aging_backlog': aging_backlog,
                'stalled_in_progress': stalled_in_progress
            },
            'individual_performance': individual_metrics,
            'team_overview': team_overview,
            'trend_metrics': trend_metrics,
            'forecast': forecast,
            'risk_alerts': risk_alerts
        }

    async def get_individual_deep_dive(self, assignee: str, date_range: str = '30d') -> Dict[str, Any]:
        days = self._parse_range_days(date_range)
        since = datetime.utcnow() - timedelta(days=days)
        jql = f'assignee = "{assignee}" AND updated >= "{since.strftime("%Y-%m-%d")}" ORDER BY updated DESC'

        try:
            tickets = await self.jira.search_tickets(custom_jql=jql, max_results=1000)
        except Exception as e:
            logger.error(f"Individual deep dive search failed: {e}")
            return {"error": "jira_search_failed", "detail": str(e)}

        norm: List[Dict[str, Any]] = []
        for t in tickets:
            if not isinstance(t, dict):
                continue
            status = (t.get('status') or '').strip()
            created = self._parse_dt(t.get('created'))
            resolved = self._parse_dt(t.get('resolutionDate'))
            norm.append({
                'key': t.get('key'),
                'summary': t.get('summary'),
                'status': status,
                'created': created.isoformat() if created else None,
                'resolved': resolved.isoformat() if resolved else None
            })

        done = [t for t in norm if (t['status'] or '').lower() in RESOLVED_STATUSES]
        in_progress = [t for t in norm if (t['status'] or '').lower() in ACTIVE_STATUSES]
        todo = [t for t in norm if (t['status'] or '').lower() in TODO_STATUSES]
        total = len(norm)
        completion_rate = round((len(done) / total) * 100, 2) if total else 0

        resolution_times: List[float] = []
        for t in done:
            if t['created'] and t['resolved']:
                try:
                    c = self._parse_dt(t['created'])
                    r = self._parse_dt(t['resolved'])
                    if c and r and r >= c:
                        resolution_times.append((r - c).total_seconds() / 86400.0)
                except Exception:
                    continue
        try:
            avg_resolution = round(statistics.mean(resolution_times), 2) if resolution_times else 0.0
        except statistics.StatisticsError:
            avg_resolution = 0.0

        return {
            'assignee': assignee,
            'range_days': days,
            'stats': {
                'done': len(done),
                'progress': len(in_progress),
                'todo': len(todo),
                'total': total,
                'completion_rate': completion_rate,
                'avg_resolution_days': avg_resolution
            },
            'tickets': norm
        }

    # ---------------- Helpers ---------------- #
    def _parse_range_days(self, r: str) -> int:
        try:
            if r.endswith('d'):
                return int(r[:-1])
            if r.endswith('w'):
                return int(r[:-1]) * 7
        except Exception:
            pass
        return 30

    def _parse_dt(self, v: Optional[str]):
        if not v:
            return None
        for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ"):
            try:
                return datetime.strptime(v, fmt).replace(tzinfo=None)
            except Exception:
                continue
        return None

    def _compute_score(self, done: int, progress: int, todo: int, completion_rate: float) -> int:
        total = done + progress + todo
        activity_factor = min(total / 20, 1.0)  # saturate after 20 tickets
        completion_factor = completion_rate / 100
        raw = (0.55 * completion_factor + 0.35 * activity_factor + 0.10 * (done / (total or 1))) * 100
        return int(round(min(raw, 100)))
