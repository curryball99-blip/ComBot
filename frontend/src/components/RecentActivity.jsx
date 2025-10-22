import { useCallback, useEffect, useState } from 'react';

// Simple Recent Activity component restored from legacy implementation
// Uses new backend endpoints: /api/jira/recent and GET /api/jira/search
// Will attempt /api/jira/recent first (fast path) and fall back to /api/jira/search if filters/customJql applied.

const STATUS_COLOR_MAP = {
    Open: '#2563eb',
    'In Progress': '#9333ea',
    'In Review': '#6366f1',
    Testing: '#f59e0b',
    Paused: '#64748b',
    Done: '#16a34a',
    Closed: '#16a34a',
    Resolved: '#16a34a'
};

const priorityColor = (p) => {
    if (!p) return '#64748b';
    const v = p.toLowerCase();
    if (v.includes('high') || v.includes('block')) return '#dc2626';
    if (v.includes('med')) return '#d97706';
    return '#64748b';
};

// Derive API base (reuse logic pattern from api.js minimal version)
const getApiBase = () => {
    try {
        if (process.env.REACT_APP_API_URL && process.env.REACT_APP_API_URL.trim()) {
            return process.env.REACT_APP_API_URL.replace(/\/$/, '');
        }
        const { protocol, hostname } = window.location;
        const isLocal = ['localhost', '127.0.0.1'].includes(hostname);
        if (isLocal) return 'http://localhost:8000';
        return `${protocol}//${hostname}:8000`;
    } catch {
        return 'http://localhost:8000';
    }
};
const API_BASE = getApiBase();

export const RecentActivity = ({
    projectKey = 'MBSL3',
    limit = 15,
    autoRefreshMs = 60000,
    compact = false,
    status,
    priority,
    assignee,
    customJql,
    quickFilter // matches backend quick_filter param (ACTIVE_MBSL3, RECENT_UPDATES, HIGH_PRIORITY)
}) => {
    const [tickets, setTickets] = useState([]);
    const [loading, setLoading] = useState(false);
    const [err, setErr] = useState(null);
    const [lastUpdated, setLastUpdated] = useState(null);

    const buildParams = () => {
        const params = new URLSearchParams();
        params.set('max_results', String(limit));
        if (customJql) {
            params.set('custom_jql', customJql);
            return params;
        }
        if (status) params.set('status', status);
        if (priority) params.set('priority', priority);
        if (assignee) params.set('assignee', assignee);
        // Provide a base query for project scoping if not using customJql
        params.set('query', `project = "${projectKey}" ORDER BY updated DESC`);
        return params;
    };

    const fetchTickets = useCallback(async () => {
        setLoading(true);
        setErr(null);
        try {
            let list = [];
            // Fast path: no filters -> use /api/jira/recent
            if (!customJql && !status && !priority && !assignee) {
                const recentParams = new URLSearchParams();
                recentParams.set('project_key', projectKey);
                recentParams.set('limit', String(limit));
                if (quickFilter && quickFilter !== 'ALL') {
                    recentParams.set('quick_filter', quickFilter);
                }
                const recent = await fetch(`${API_BASE}/api/jira/recent?${recentParams.toString()}`);
                if (recent.ok) {
                    const data = await recent.json();
                    list = (data.tickets || []).slice(0, limit);
                } else {
                    const txt = await recent.text();
                    console.warn('Recent endpoint error', recent.status, txt);
                }
            }
            // Fallback or filtered path
            if (list.length === 0 || customJql || status || priority || assignee) {
                const params = buildParams();
                const res = await fetch(`${API_BASE}/api/jira/search?${params.toString()}`);
                if (!res.ok) {
                    const txt = await res.text();
                    throw new Error(`HTTP ${res.status} ${txt.slice(0, 160)}`);
                }
                const data = await res.json();
                list = (data.tickets || []).slice(0, limit);
            }
            setTickets(list);
            setLastUpdated(new Date().toLocaleTimeString());
        } catch (e) {
            setErr(e.message || 'Failed to load recent activity');
        } finally {
            setLoading(false);
        }
    }, [projectKey, limit, customJql, status, priority, assignee, quickFilter]);

    useEffect(() => {
        fetchTickets();
        const id = setInterval(fetchTickets, autoRefreshMs);
        return () => clearInterval(id);
    }, [fetchTickets, autoRefreshMs]);

    return (
        <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12, padding: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>Recent Activity</h3>
                <div style={{ fontSize: 12, color: '#64748b' }}>
                    {loading ? 'Refreshing...' : lastUpdated ? `Updated ${lastUpdated}` : ''}
                </div>
            </div>
            {err && (
                <div style={{ background: '#fef2f2', color: '#b91c1c', padding: '8px 10px', borderRadius: 6, fontSize: 12 }}>
                    {err}
                </div>
            )}
            {(!loading && tickets.length === 0 && !err) && (
                <div style={{ fontSize: 13, color: '#64748b', padding: '8px 4px' }}>
                    No recent tickets found.
                </div>
            )}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: compact ? 320 : 540, overflowY: 'auto' }}>
                {tickets.map(t => {
                    const statusColor = STATUS_COLOR_MAP[t.status || ''] || '#475569';
                    return (
                        <div
                            key={t.key}
                            style={{
                                border: '1px solid #f1f5f9',
                                borderRadius: 10,
                                padding: '10px 12px',
                                background: '#f8fafc',
                                display: 'flex',
                                flexDirection: 'column',
                                gap: 4
                            }}
                        >
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                                <a
                                    href={t.url || `https://your-domain.atlassian.net/browse/${t.key}`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    style={{ fontWeight: 600, fontSize: 13, color: '#1d4ed8', textDecoration: 'none' }}
                                >
                                    {t.key}
                                </a>
                                {t.status && (
                                    <span
                                        style={{
                                            background: statusColor,
                                            color: '#fff',
                                            fontSize: 11,
                                            padding: '2px 8px',
                                            borderRadius: 999
                                        }}
                                    >
                                        {t.status}
                                    </span>
                                )}
                                {t.issueType && (
                                    <span
                                        style={{
                                            background: '#e2e8f0',
                                            color: '#334155',
                                            fontSize: 11,
                                            padding: '2px 8px',
                                            borderRadius: 999
                                        }}
                                    >
                                        {t.issueType}
                                    </span>
                                )}
                                {t.priority && (
                                    <span
                                        style={{
                                            background: priorityColor(t.priority),
                                            color: '#fff',
                                            fontSize: 11,
                                            padding: '2px 8px',
                                            borderRadius: 999
                                        }}
                                    >
                                        {t.priority}
                                    </span>
                                )}
                                {t.assignee && t.assignee !== 'Unassigned' && (
                                    <span style={{ fontSize: 11, color: '#475569' }}>• {t.assignee}</span>
                                )}
                            </div>
                            <div style={{ fontSize: 13, color: '#0f172a', lineHeight: 1.3 }}>
                                {t.summary || '(No summary)'}
                            </div>
                            {t.updated && (
                                <div style={{ fontSize: 11, color: '#64748b' }}>
                                    Updated: {new Date(t.updated).toLocaleString()}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
            <div style={{ marginTop: 10, display: 'flex', gap: 8 }}>
                <button
                    onClick={fetchTickets}
                    style={{
                        background: '#2563eb',
                        color: '#fff',
                        border: 'none',
                        padding: '6px 12px',
                        fontSize: 12,
                        borderRadius: 6,
                        cursor: 'pointer'
                    }}
                    disabled={loading}
                >
                    {loading ? 'Refreshing...' : 'Refresh'}
                </button>
            </div>
        </div>
    );
};

export default RecentActivity;