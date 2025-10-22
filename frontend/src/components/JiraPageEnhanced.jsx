import { AlertCircle, BarChart3, Brain, CheckCircle, Clock, ExternalLink, Loader2, Play, Search, Target, TrendingUp, User, Users } from 'lucide-react';
import { useEffect, useState } from 'react';

// API base selection: use env or fallback to matching backend port
const API_BASE = (process.env.REACT_APP_API_URL || '').replace(/\/$/, '') || `${window.location.protocol}//${window.location.hostname}:8000`;

const JiraPageEnhanced = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [teamAnalytics, setTeamAnalytics] = useState(null);
  const [selectedMember, setSelectedMember] = useState(null);
  const [individualAnalysis, setIndividualAnalysis] = useState(null);
  const [teamFilters, setTeamFilters] = useState({ assignees: [], dateRange: '30d' });
  const [showAssigneeDropdown, setShowAssigneeDropdown] = useState(false);
  const [globalJql, setGlobalJql] = useState('');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [dashboardData, setDashboardData] = useState(null);
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [customJql, setCustomJql] = useState('');
  const [aiAnalysis, setAiAnalysis] = useState(null);
  const [analyzingTicket, setAnalyzingTicket] = useState(null);
  const [dateRange, setDateRange] = useState('7d');
  const [filters, setFilters] = useState({ assignee: '', status: '', priority: '' });
  const [filterOptions, setFilterOptions] = useState({ assignees: [], statuses: [], priorities: [] });
  const [currentPage, setCurrentPage] = useState(1);
  const [pagination, setPagination] = useState({});

  useEffect(() => {
    if (activeTab === 'dashboard') {
      loadDashboard();
      loadFilterOptions();
    } else if (activeTab === 'team-analytics') {
      loadTeamAnalytics();
    }
  }, [activeTab, dateRange, teamFilters, globalJql]);

  const loadDashboard = async () => {
    setLoading(true);
    try {
      const range = dateRange || '30d';
      const response = await fetch(`${API_BASE}/api/jira/live/summary?range=${encodeURIComponent(range)}`);
      if (response.ok) {
        const live = await response.json();
        const transformed = {
          summary: {
            total_tickets: live.total,
            active_tickets: live.active,
            resolved_tickets: live.resolved,
            active_percentage: live.active_pct,
            resolved_percentage: live.resolved_pct,
            recent_updates: 0
          },
          status_distribution: live.status_distribution || {},
          priority_distribution: live.priority_distribution || {},
          assignee_distribution: Object.fromEntries((live.assignee_top || []).map(([n, c]) => [n, c])),
          recent_tickets: []
        };
        setDashboardData(transformed);
      }
    } catch (e) {
      console.error('Failed to load live summary:', e);
    } finally { setLoading(false); }
  };

  const loadFilterOptions = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/jira/filters`);
      const data = await response.json();
      if (response.ok) {
        setFilterOptions(data);
      }
    } catch (error) {
      console.error('Failed to load filter options:', error);
    }
  };

  const loadTeamAnalytics = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.append('date_range', teamFilters.dateRange);
      if (globalJql.trim()) params.append('jql', globalJql.trim());
      const response = await fetch(`${API_BASE}/api/jira/team-analytics?${params}`);
      const data = await response.json();
      if (response.ok) {
        setTeamAnalytics(data);
      }
    } catch (error) {
      console.error('Failed to load team analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadIndividualAnalysis = async (assignee) => {
    try {
      const response = await fetch(`${API_BASE}/api/jira/individual-analysis/${encodeURIComponent(assignee)}?date_range=${teamFilters.dateRange}`);
      const data = await response.json();
      if (response.ok) {
        setIndividualAnalysis(data);
        setSelectedMember(assignee);
      }
    } catch (error) {
      console.error('Failed to load individual analysis:', error);
    }
  };

  const searchTickets = async (page = 1) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: page.toString(), limit: '20' });
      if (globalJql.trim()) {
        params.append('custom_jql', globalJql.trim());
      } else if (customJql.trim()) {
        params.append('custom_jql', customJql.trim());
      } else if (searchQuery.trim()) {
        params.append('query', searchQuery.trim());
      }
      if (filters.assignee) params.append('assignee', filters.assignee);
      if (filters.status) params.append('status', filters.status);
      if (filters.priority) params.append('priority', filters.priority);
      const response = await fetch(`${API_BASE}/api/jira/search?${params}`);
      const data = await response.json();
      if (response.ok) {
        setTickets(data.tickets || []);
        setPagination(data.pagination || {});
        setCurrentPage(page);
      } else {
        console.error('Search failed:', data.detail);
        setTickets([]);
      }
    } catch (error) {
      console.error('Search error:', error);
      setTickets([]);
    } finally {
      setLoading(false);
    }
  };

  const analyzeTicket = async (ticketKey) => {
    setAnalyzingTicket(ticketKey);
    try {
      const response = await fetch('/api/jira/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticket_key: ticketKey })
      });

      if (response.ok) {
        const result = await response.json();
        setAiAnalysis(result);
      }
    } catch (error) {
      console.error('Analysis failed:', error);
    } finally {
      setAnalyzingTicket(null);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 shadow-sm border-b dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-3">
              <ExternalLink className="w-8 h-8 text-blue-600" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">MBSL3 JIRA Analytics</h1>
                <p className="text-sm text-gray-500 dark:text-gray-400">Enhanced ticket management and AI analysis</p>
              </div>
            </div>

            {/* Tabs */}
            <div className="flex space-x-1 bg-gray-100 dark:bg-gray-700 p-1 rounded-lg">
              <button
                onClick={() => setActiveTab('dashboard')}
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === 'dashboard'
                    ? 'bg-white dark:bg-gray-600 text-blue-600 dark:text-blue-400 shadow-sm'
                    : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                  }`}
              >
                <BarChart3 size={14} className="inline mr-1" />
                Dashboard
              </button>
              <button
                onClick={() => setActiveTab('search')}
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === 'search'
                    ? 'bg-white dark:bg-gray-600 text-blue-600 dark:text-blue-400 shadow-sm'
                    : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                  }`}
              >
                <Search size={14} className="inline mr-1" />
                Search
              </button>
              <button
                onClick={() => setActiveTab('team-analytics')}
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === 'team-analytics'
                    ? 'bg-white dark:bg-gray-600 text-blue-600 dark:text-blue-400 shadow-sm'
                    : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                  }`}
              >
                <Users size={14} className="inline mr-1" />
                Analytics
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6" onClick={() => setShowAssigneeDropdown(false)}>

        {/* Dashboard Tab */}
        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            {/* Date Range Filter */}
            <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow-sm">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium dark:text-white">MBSL3 Project Overview</h3>
                <select
                  value={dateRange}
                  onChange={(e) => setDateRange(e.target.value)}
                  className="px-3 py-1 border dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded text-sm"
                >
                  <option value="7d">Last 7 days</option>
                  <option value="30d">Last 30 days</option>
                  <option value="90d">Last 90 days</option>
                </select>
              </div>
            </div>

            {loading ? (
              <div className="text-center py-12">
                <Loader2 className="w-8 h-8 animate-spin mx-auto text-blue-600" />
                <p className="mt-2 text-gray-600 dark:text-gray-400">Loading dashboard...</p>
              </div>
            ) : dashboardData?.error ? (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                <div className="flex items-center">
                  <AlertCircle className="w-5 h-5 text-red-500 mr-2" />
                  <span className="text-red-700 dark:text-red-400">{dashboardData.error}</span>
                </div>
              </div>
            ) : dashboardData ? (
              <>
                {/* Summary Cards */}
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                  <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow-sm border-l-4 border-blue-500">
                    <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                      {dashboardData.summary?.total_tickets || 0}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">Total Tickets</div>
                  </div>

                  <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow-sm border-l-4 border-green-500">
                    <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                      {dashboardData.summary?.active_tickets || 0}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">
                      Active ({dashboardData.summary?.active_percentage || 0}%)
                    </div>
                  </div>

                  <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow-sm border-l-4 border-gray-500">
                    <div className="text-2xl font-bold text-gray-600 dark:text-gray-400">
                      {dashboardData.summary?.resolved_tickets || 0}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">
                      Resolved ({dashboardData.summary?.resolved_percentage || 0}%)
                    </div>
                  </div>

                  <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow-sm border-l-4 border-purple-500">
                    <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                      {dashboardData.summary?.recent_updates || 0}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">Recent Updates</div>
                  </div>

                  <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow-sm border-l-4 border-orange-500">
                    <div className="text-2xl font-bold text-orange-600 dark:text-orange-400">
                      {Object.keys(dashboardData.assignee_distribution || {}).length}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">Active Assignees</div>
                  </div>
                </div>

                {/* Distribution Charts */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  {/* Status Distribution */}
                  <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow-sm">
                    <h3 className="font-medium mb-3 dark:text-white">By Status</h3>
                    <div className="space-y-2">
                      {Object.entries(dashboardData.status_distribution || {}).slice(0, 5).map(([status, count]) => (
                        <div key={status} className="flex justify-between text-sm">
                          <span className="text-gray-600 dark:text-gray-400 truncate">{status}</span>
                          <span className="font-medium dark:text-white">{count}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Priority Distribution */}
                  <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow-sm">
                    <h3 className="font-medium mb-3 dark:text-white">By Priority</h3>
                    <div className="space-y-2">
                      {Object.entries(dashboardData.priority_distribution || {}).slice(0, 5).map(([priority, count]) => (
                        <div key={priority} className="flex justify-between text-sm">
                          <span className="text-gray-600 dark:text-gray-400 truncate">{priority}</span>
                          <span className="font-medium dark:text-white">{count}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Type Distribution */}
                  <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow-sm">
                    <h3 className="font-medium mb-3 dark:text-white">By Type</h3>
                    <div className="space-y-2">
                      {Object.entries(dashboardData.type_distribution || {}).slice(0, 5).map(([type, count]) => (
                        <div key={type} className="flex justify-between text-sm">
                          <span className="text-gray-600 dark:text-gray-400 truncate">{type}</span>
                          <span className="font-medium dark:text-white">{count}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Top Assignees */}
                  <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow-sm">
                    <h3 className="font-medium mb-3 dark:text-white">Top Assignees</h3>
                    <div className="space-y-2">
                      {Object.entries(dashboardData.assignee_distribution || {}).slice(0, 5).map(([assignee, count]) => (
                        <div key={assignee} className="flex justify-between text-sm">
                          <span className="text-gray-600 dark:text-gray-400 truncate">{assignee}</span>
                          <span className="font-medium dark:text-white">{count}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Recent Tickets */}
                {dashboardData.recent_tickets && dashboardData.recent_tickets.length > 0 && (
                  <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm">
                    <h3 className="text-lg font-semibold mb-4 dark:text-white">Recent Activity</h3>
                    <div className="space-y-2 max-h-96 overflow-y-auto">
                      {dashboardData.recent_tickets.slice(0, 15).map((ticket) => (
                        <div key={ticket.key} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center space-x-2 mb-1">
                              <span className="font-medium text-blue-600 dark:text-blue-400">{ticket.key}</span>
                              <span className="text-xs text-gray-500 dark:text-gray-400">• {ticket.assignee}</span>
                              <span className={`px-2 py-1 text-xs rounded-full ${ticket.status === 'Done' ? 'bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200' :
                                  ticket.status === 'In Progress' ? 'bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200' :
                                    'bg-gray-100 dark:bg-gray-600 text-gray-800 dark:text-gray-200'
                                }`}>
                                {ticket.status}
                              </span>
                            </div>
                            <p className="text-sm text-gray-600 dark:text-gray-300 truncate">{ticket.summary}</p>
                          </div>
                          <div className="flex items-center space-x-2">
                            {!['Done', 'Closed', 'Rejected', 'Resolved'].includes(ticket.status) && (
                              <button
                                onClick={() => analyzeTicket(ticket.key)}
                                disabled={analyzingTicket === ticket.key}
                                className="p-2 text-purple-600 hover:text-purple-800 dark:text-purple-400 dark:hover:text-purple-300 disabled:opacity-50 rounded"
                                title="AI Analysis"
                              >
                                {analyzingTicket === ticket.key ? (
                                  <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                  <Brain className="w-4 h-4" />
                                )}
                              </button>
                            )}
                            <a
                              href={ticket.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="p-2 text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-400 rounded"
                            >
                              <ExternalLink className="w-4 h-4" />
                            </a>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="text-center py-12 text-gray-500 dark:text-gray-400">No dashboard data available</div>
            )}
          </div>
        )}

        {/* Search Tab */}
        {activeTab === 'search' && (
          <div className="space-y-6">
            {/* Search Section */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
              <div className="space-y-4">
                {/* Basic Search */}
                <div className="flex items-center gap-4">
                  <div className="flex-1">
                    <input
                      type="text"
                      placeholder="Search tickets (key, project, or summary)..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && searchTickets()}
                      className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                  <button
                    onClick={() => searchTickets()}
                    disabled={loading}
                    className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
                  >
                    {loading ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Search className="w-4 h-4" />
                    )}
                    Search
                  </button>
                </div>

                {/* Custom JQL */}
                <div className="flex items-center gap-4">
                  <div className="flex-1">
                    <input
                      type="text"
                      placeholder="Custom JQL Query (e.g., project = MBSL3 AND status = Open)..."
                      value={customJql}
                      onChange={(e) => setCustomJql(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && searchTickets()}
                      className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
                    />
                  </div>
                </div>

                {/* Filters */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <select
                    value={filters.assignee}
                    onChange={(e) => setFilters({ ...filters, assignee: e.target.value })}
                    className="px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg"
                  >
                    <option value="">All Assignees</option>
                    {filterOptions.assignees.map(assignee => (
                      <option key={assignee} value={assignee}>{assignee}</option>
                    ))}
                  </select>

                  <select
                    value={filters.status}
                    onChange={(e) => setFilters({ ...filters, status: e.target.value })}
                    className="px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg"
                  >
                    <option value="">All Statuses</option>
                    {filterOptions.statuses.map(status => (
                      <option key={status} value={status}>{status}</option>
                    ))}
                  </select>

                  <select
                    value={filters.priority}
                    onChange={(e) => setFilters({ ...filters, priority: e.target.value })}
                    className="px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg"
                  >
                    <option value="">All Priorities</option>
                    {filterOptions.priorities.map(priority => (
                      <option key={priority} value={priority}>{priority}</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            {/* Results */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
              {loading ? (
                <div className="text-center py-8">
                  <Loader2 className="w-8 h-8 animate-spin mx-auto text-blue-600" />
                  <p className="mt-2 text-gray-600 dark:text-gray-400">Searching...</p>
                </div>
              ) : (
                <>
                  {tickets.length > 0 && (
                    <div className="flex justify-between items-center mb-4">
                      <h3 className="text-lg font-semibold dark:text-white">
                        Search Results ({pagination.total || tickets.length})
                      </h3>
                      {pagination.has_more && (
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => searchTickets(currentPage - 1)}
                            disabled={currentPage === 1}
                            className="px-3 py-1 bg-blue-600 text-white rounded disabled:opacity-50 hover:bg-blue-700"
                          >
                            ←
                          </button>
                          <span className="text-sm text-gray-600 dark:text-gray-400">
                            Page {currentPage}
                          </span>
                          <button
                            onClick={() => searchTickets(currentPage + 1)}
                            disabled={!pagination.has_more}
                            className="px-3 py-1 bg-blue-600 text-white rounded disabled:opacity-50 hover:bg-blue-700"
                          >
                            →
                          </button>
                        </div>
                      )}
                    </div>
                  )}

                  <div className="space-y-2">
                    {tickets.map((ticket) => (
                      <div key={ticket.key} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-2 mb-1">
                            <span className="font-medium text-blue-600 dark:text-blue-400">{ticket.key}</span>
                            <span className="text-xs text-gray-500 dark:text-gray-400">• {ticket.assignee}</span>
                            <span className={`px-2 py-1 text-xs rounded-full ${ticket.status === 'Done' ? 'bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200' :
                                ticket.status === 'In Progress' ? 'bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200' :
                                  'bg-gray-100 dark:bg-gray-600 text-gray-800 dark:text-gray-200'
                              }`}>
                              {ticket.status}
                            </span>
                            {ticket.priority && (
                              <span className="text-xs text-gray-500 dark:text-gray-400">
                                {ticket.priority}
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-gray-600 dark:text-gray-300 truncate">{ticket.summary}</p>
                        </div>
                        <div className="flex items-center space-x-2">
                          {!['Done', 'Closed', 'Rejected', 'Resolved'].includes(ticket.status) && (
                            <button
                              onClick={() => analyzeTicket(ticket.key)}
                              disabled={analyzingTicket === ticket.key}
                              className="p-2 text-purple-600 hover:text-purple-800 dark:text-purple-400 dark:hover:text-purple-300 disabled:opacity-50 rounded"
                              title="AI Analysis"
                            >
                              {analyzingTicket === ticket.key ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                              ) : (
                                <Brain className="w-4 h-4" />
                              )}
                            </button>
                          )}
                          <a
                            href={ticket.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="p-2 text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-400 rounded"
                          >
                            <ExternalLink className="w-4 h-4" />
                          </a>
                        </div>
                      </div>
                    ))}
                  </div>

                  {tickets.length === 0 && !loading && (
                    <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                      No tickets found. Try adjusting your search criteria.
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        )}

        {/* Team Analytics Tab */}
        {activeTab === 'team-analytics' && (
          <div className="space-y-6">
            {/* Analytics Filters */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-4">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium dark:text-white flex items-center">
                  <Users className="w-5 h-5 mr-2 text-purple-600" />
                  Team Productivity Analytics
                </h3>
                <div className="flex items-center gap-4">
                  <div className="relative">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setShowAssigneeDropdown(!showAssigneeDropdown);
                      }}
                      className="px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg text-sm min-w-48 text-left flex items-center justify-between"
                    >
                      <span>
                        {teamFilters.assignees.length === 0 ? 'All Team Members' :
                          teamFilters.assignees.length === 1 ? teamFilters.assignees[0] :
                            `${teamFilters.assignees.length} members selected`}
                      </span>
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>

                    {showAssigneeDropdown && (
                      <div
                        className="absolute z-10 mt-1 w-full bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg max-h-48 overflow-y-auto"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <div className="p-2">
                          <label className="flex items-center p-2 hover:bg-gray-100 dark:hover:bg-gray-600 rounded cursor-pointer">
                            <input
                              type="checkbox"
                              checked={teamFilters.assignees.length === 0}
                              onChange={() => setTeamFilters({ ...teamFilters, assignees: [] })}
                              className="mr-2"
                            />
                            <span className="text-sm dark:text-white">All Team Members</span>
                          </label>
                          {filterOptions.assignees.map(assignee => (
                            <label key={assignee} className="flex items-center p-2 hover:bg-gray-100 dark:hover:bg-gray-600 rounded cursor-pointer">
                              <input
                                type="checkbox"
                                checked={teamFilters.assignees.includes(assignee)}
                                onChange={(e) => {
                                  if (e.target.checked) {
                                    setTeamFilters({ ...teamFilters, assignees: [...teamFilters.assignees, assignee] });
                                  } else {
                                    setTeamFilters({ ...teamFilters, assignees: teamFilters.assignees.filter(a => a !== assignee) });
                                  }
                                }}
                                className="mr-2"
                              />
                              <span className="text-sm dark:text-white">{assignee}</span>
                            </label>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                  <select
                    value={teamFilters.dateRange}
                    onChange={(e) => setTeamFilters({ ...teamFilters, dateRange: e.target.value })}
                    className="px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg text-sm"
                  >
                    <option value="7d">Last 7 days</option>
                    <option value="30d">Last 30 days</option>
                    <option value="90d">Last 90 days</option>
                  </select>
                </div>
              </div>
            </div>

            {loading ? (
              <div className="text-center py-12">
                <Loader2 className="w-8 h-8 animate-spin mx-auto text-blue-600" />
                <p className="mt-2 text-gray-600 dark:text-gray-400">Loading team analytics...</p>
              </div>
            ) : teamAnalytics && (
              <>
                {/* Summary Cards */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  {teamAnalytics.summary_cards?.map((card, index) => (
                    <div key={index} className={`bg-white dark:bg-gray-800 p-4 rounded-lg shadow-sm border-l-4 border-${card.color}-500`}>
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium text-gray-600 dark:text-gray-400">{card.title}</p>
                          <p className={`text-2xl font-bold text-${card.color}-600 dark:text-${card.color}-400`}>
                            {card.value}
                          </p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">{card.subtitle}</p>
                        </div>
                        <div className={`p-2 bg-${card.color}-100 dark:bg-${card.color}-900/20 rounded-full`}>
                          {card.title === 'Team Members' && <Users className={`w-5 h-5 text-${card.color}-600`} />}
                          {card.title === 'Total Tickets' && <Target className={`w-5 h-5 text-${card.color}-600`} />}
                          {card.title === 'Avg Completion' && <CheckCircle className={`w-5 h-5 text-${card.color}-600`} />}
                          {card.title === 'Avg Resolution' && <Clock className={`w-5 h-5 text-${card.color}-600`} />}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Individual Performance with Scrollbar */}
                <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
                  <h3 className="text-lg font-semibold mb-4 dark:text-white flex items-center">
                    <User className="w-5 h-5 mr-2 text-blue-600" />
                    Individual Performance
                  </h3>

                  <div className="max-h-96 overflow-y-auto pr-2">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {teamAnalytics.individual_performance
                        ?.filter(person => teamFilters.assignees.length === 0 || teamFilters.assignees.includes(person.assignee))
                        .map((person, index) => (
                          <div
                            key={index}
                            onClick={() => loadIndividualAnalysis(person.assignee)}
                            className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer transition-colors"
                          >
                            <div className="flex items-center justify-between mb-3">
                              <h4 className="font-medium text-gray-900 dark:text-white truncate text-sm">
                                {person.assignee}
                              </h4>
                              <div className={`px-2 py-1 rounded-full text-xs font-medium ${person.productivity_score >= 80 ? 'text-green-600 bg-green-100 dark:bg-green-900/20' :
                                  person.productivity_score >= 60 ? 'text-yellow-600 bg-yellow-100 dark:bg-yellow-900/20' :
                                    'text-red-600 bg-red-100 dark:bg-red-900/20'
                                }`}>
                                {person.productivity_score}
                              </div>
                            </div>

                            <div className="grid grid-cols-3 gap-2 text-xs mb-3">
                              <div className="text-center">
                                <div className="flex items-center justify-center mb-1">
                                  <CheckCircle className="w-3 h-3 text-green-500 mr-1" />
                                  <span className="font-medium">{person.metrics.done}</span>
                                </div>
                                <p className="text-gray-500 dark:text-gray-400">Done</p>
                              </div>
                              <div className="text-center">
                                <div className="flex items-center justify-center mb-1">
                                  <Play className="w-3 h-3 text-blue-500 mr-1" />
                                  <span className="font-medium">{person.metrics.in_progress}</span>
                                </div>
                                <p className="text-gray-500 dark:text-gray-400">Progress</p>
                              </div>
                              <div className="text-center">
                                <div className="flex items-center justify-center mb-1">
                                  <Clock className="w-3 h-3 text-gray-500 mr-1" />
                                  <span className="font-medium">{person.metrics.todo}</span>
                                </div>
                                <p className="text-gray-500 dark:text-gray-400">To Do</p>
                              </div>
                            </div>

                            <div className="flex items-center justify-between text-xs">
                              <span className="text-gray-500 dark:text-gray-400">Completion: {person.completion_rate}%</span>
                              <div className="flex items-center">
                                {person.performance_trend === 'improving' && <TrendingUp className="w-3 h-3 text-green-500" />}
                                {person.performance_trend === 'declining' && <AlertCircle className="w-3 h-3 text-red-500" />}
                                {person.performance_trend === 'stable' && <BarChart3 className="w-3 h-3 text-gray-500" />}
                                <span className="ml-1 text-gray-500 dark:text-gray-400 capitalize">{person.performance_trend}</span>
                              </div>
                            </div>
                          </div>
                        ))}
                    </div>
                  </div>
                </div>

                {/* AI Insights */}
                <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
                  <h3 className="text-lg font-semibold mb-4 dark:text-white flex items-center">
                    <Brain className="w-5 h-5 mr-2 text-purple-600" />
                    AI Productivity Insights
                  </h3>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-h-64 overflow-y-auto">
                    {teamAnalytics.productivity_insights
                      ?.filter(insight => teamFilters.assignees.length === 0 || teamFilters.assignees.includes(insight.assignee))
                      .map((insight, index) => (
                        <div key={index} className="border-l-4 border-purple-500 pl-4 py-2">
                          <h4 className="font-medium text-sm text-gray-900 dark:text-white mb-2">
                            {insight.assignee}
                          </h4>
                          <div className="space-y-2">
                            {insight.insights.map((item, idx) => (
                              <div key={idx} className={`p-2 rounded text-xs ${item.type === 'positive' ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300' :
                                  item.type === 'concern' ? 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300' :
                                    item.type === 'warning' ? 'bg-yellow-50 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-300' :
                                      'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                                }`}>
                                {item.message}
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                  </div>
                </div>
              </>
            )}
          </div>
        )}
      </div>

      {/* Individual Analysis Modal */}
      {selectedMember && individualAnalysis && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg w-full max-w-6xl h-5/6 flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b dark:border-gray-700">
              <div className="flex items-center space-x-3">
                <User className="w-6 h-6 text-blue-600" />
                <div>
                  <h2 className="text-xl font-semibold dark:text-white">{selectedMember}</h2>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Individual Performance Analysis</p>
                </div>
              </div>
              <button
                onClick={() => { setSelectedMember(null); setIndividualAnalysis(null); }}
                className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 text-2xl"
              >
                ×
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6">
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Performance Summary */}
                <div className="lg:col-span-1">
                  <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 mb-4">
                    <h3 className="font-semibold mb-3 dark:text-white">Performance Summary</h3>
                    {individualAnalysis.performance_summary && (
                      <div className="space-y-3">
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600 dark:text-gray-400">Completion Rate:</span>
                          <span className="font-medium dark:text-white">
                            {individualAnalysis.performance_summary.completion_rate}%
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600 dark:text-gray-400">Avg Resolution:</span>
                          <span className="font-medium dark:text-white">
                            {individualAnalysis.performance_summary.avg_resolution_days} days
                          </span>
                        </div>
                        <div className="mt-4">
                          <h4 className="text-sm font-medium mb-2 dark:text-white">Status Breakdown:</h4>
                          {Object.entries(individualAnalysis.performance_summary.status_breakdown || {}).map(([status, count]) => (
                            <div key={status} className="flex justify-between text-xs mb-1">
                              <span className="text-gray-600 dark:text-gray-400">{status}:</span>
                              <span className="dark:text-white">{count}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* AI Insights */}
                  <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4">
                    <h3 className="font-semibold mb-3 text-purple-800 dark:text-purple-300 flex items-center">
                      <Brain className="w-4 h-4 mr-2" />
                      AI Insights
                    </h3>
                    <div className="space-y-2">
                      {individualAnalysis.performance_summary?.productivity_insights?.map((insight, idx) => (
                        <p key={idx} className="text-xs text-purple-700 dark:text-purple-300">
                          {insight}
                        </p>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Ticket Timeline */}
                <div className="lg:col-span-2">
                  <h3 className="font-semibold mb-4 dark:text-white">Recent Tickets</h3>
                  <div className="space-y-2 max-h-96 overflow-y-auto">
                    {individualAnalysis.status_timeline?.slice(0, 20).map((ticket, idx) => (
                      <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-2 mb-1">
                            <span className="font-medium text-blue-600 dark:text-blue-400 text-sm">
                              {ticket.key}
                            </span>
                            <span className={`px-2 py-1 text-xs rounded-full ${ticket.status === 'Done' ? 'bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200' :
                                ticket.status === 'In Progress' ? 'bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200' :
                                  'bg-gray-100 dark:bg-gray-600 text-gray-800 dark:text-gray-200'
                              }`}>
                              {ticket.status}
                            </span>
                            {ticket.priority && (
                              <span className="text-xs text-gray-500 dark:text-gray-400">
                                {ticket.priority}
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-gray-600 dark:text-gray-300 truncate">
                            {ticket.summary}
                          </p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">
                            Updated: {new Date(ticket.updated).toLocaleDateString()}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* AI Analysis Modal */}
      {aiAnalysis && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg w-full max-w-6xl h-5/6 flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b dark:border-gray-700 flex-shrink-0">
              <div className="flex items-center space-x-3">
                <Brain className="w-6 h-6 text-purple-600" />
                <div>
                  <h2 className="text-lg font-semibold dark:text-white">
                    AI Analysis: {aiAnalysis.ticket?.key} ({aiAnalysis.analysis_type})
                  </h2>
                  <p className="text-sm text-gray-500 dark:text-gray-400 truncate">
                    {aiAnalysis.ticket?.summary}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setAiAnalysis(null)}
                className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 text-2xl"
              >
                ×
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4">
              <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
                {/* Ticket Info */}
                <div className="lg:col-span-1">
                  <h3 className="text-md font-semibold mb-3 dark:text-white">Ticket Details</h3>
                  <div className="space-y-2 text-sm">
                    <div>
                      <span className="font-medium text-gray-600 dark:text-gray-400">Status:</span>
                      <span className={`ml-2 px-2 py-1 rounded-full text-xs ${aiAnalysis.ticket?.status === 'Done' ? 'bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200' :
                          aiAnalysis.ticket?.status === 'In Progress' ? 'bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200' :
                            'bg-gray-100 dark:bg-gray-600 text-gray-800 dark:text-gray-200'
                        }`}>
                        {aiAnalysis.ticket?.status}
                      </span>
                    </div>
                    <div>
                      <span className="font-medium text-gray-600 dark:text-gray-400">Assignee:</span>
                      <span className="ml-2 dark:text-gray-300">{aiAnalysis.ticket?.assignee}</span>
                    </div>
                    <div>
                      <span className="font-medium text-gray-600 dark:text-gray-400">Type:</span>
                      <span className="ml-2 dark:text-gray-300">{aiAnalysis.ticket?.issueType}</span>
                    </div>
                  </div>

                  <div className="mt-4">
                    <a
                      href={aiAnalysis.ticket?.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center space-x-2 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
                    >
                      <ExternalLink size={14} />
                      <span>Open in JIRA</span>
                    </a>
                  </div>
                </div>

                {/* AI Analysis */}
                <div className="lg:col-span-3">
                  <h3 className="text-md font-semibold mb-3 flex items-center dark:text-white">
                    <TrendingUp className="w-5 h-5 mr-2 text-purple-600" />
                    AI Analysis & Recommendations
                  </h3>

                  <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 mb-4 max-h-80 overflow-y-auto">
                    <div className="prose prose-sm dark:prose-invert max-w-none">
                      {aiAnalysis.analysis.split('\n\n').map((section, index) => {
                        if (section.includes('###') || section.includes('##')) {
                          const [title, ...content] = section.split('\n');
                          return (
                            <div key={index} className="mb-4">
                              <h4 className="font-bold text-lg text-purple-700 dark:text-purple-300 mb-2">
                                {title.replace(/#{2,3}/g, '').trim()}
                              </h4>
                              <div className="text-gray-700 dark:text-gray-300 text-sm space-y-1">
                                {content.map((line, i) => (
                                  <p key={i} className={line.includes('**') ? 'font-medium' : ''}>
                                    {line.replace(/\*\*/g, '')}
                                  </p>
                                ))}
                              </div>
                            </div>
                          );
                        }
                        return (
                          <p key={index} className="text-gray-700 dark:text-gray-300 text-sm mb-2">
                            {section.replace(/\*\*/g, '')}
                          </p>
                        );
                      })}
                    </div>
                  </div>

                  {/* Similar Tickets */}
                  {aiAnalysis.similar_tickets && aiAnalysis.similar_tickets.length > 0 && (
                    <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 mb-4">
                      <h4 className="font-medium text-blue-800 dark:text-blue-300 mb-2">Similar Historical Tickets</h4>
                      <div className="space-y-1">
                        {aiAnalysis.similar_tickets.map(ticket => (
                          <div key={ticket.key} className="text-sm text-blue-700 dark:text-blue-300">
                            <span className="font-medium">{ticket.key}</span>: {ticket.summary}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Recommendations */}
                  {aiAnalysis.recommendations && aiAnalysis.recommendations.length > 0 && (
                    <div className="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-4">
                      <h4 className="font-medium text-yellow-800 dark:text-yellow-300 mb-2">Best Practice Recommendations</h4>
                      {aiAnalysis.recommendations.map((rec, idx) => (
                        <div key={idx} className="mb-3">
                          <h5 className="font-medium text-yellow-700 dark:text-yellow-400">{rec.title}</h5>
                          <ul className="list-disc list-inside text-sm text-yellow-700 dark:text-yellow-300 ml-2">
                            {rec.items.map((item, itemIdx) => (
                              <li key={itemIdx}>{item}</li>
                            ))}
                          </ul>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="mt-3 flex items-center space-x-4 text-xs text-gray-500 dark:text-gray-400">
                    <div className="flex items-center space-x-1">
                      <Clock size={12} />
                      <span>Generated just now</span>
                    </div>
                    <div className="flex items-center space-x-1">
                      <Brain size={12} />
                      <span>Powered by Groq AI with Historical Data</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default JiraPageEnhanced;