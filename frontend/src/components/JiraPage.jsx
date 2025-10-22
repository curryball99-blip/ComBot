import { AlertCircle, BarChart3, Brain, Calendar, Clock, ExternalLink, Filter, Search, TrendingUp } from 'lucide-react';
import { useEffect, useState } from 'react';
import { jiraAPI } from '../services/api';
import LiveJiraSearch from './LiveJiraSearch';
import RecentActivity from './RecentActivity';

const JiraPage = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [dashboardData, setDashboardData] = useState(null);
  const [tickets, setTickets] = useState([]);
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [aiAnalysis, setAiAnalysis] = useState(null);
  const [analyzingTicket, setAnalyzingTicket] = useState(null);
  const [filters, setFilters] = useState({ project: 'ALL', dateRange: '7d' });
  const [currentPage, setCurrentPage] = useState(1);
  const ticketsPerPage = 10;

  useEffect(() => {
    loadProjects();
    if (activeTab === 'dashboard') {
      loadDashboard();
    }
  }, [activeTab, filters]);

  const loadProjects = async () => {
    try {
      const response = await fetch('/api/jira/projects');
      if (response.ok) {
        const data = await response.json();
        setProjects(data.projects);
      }
    } catch (error) {
      console.error('Failed to load projects:', error);
    }
  };

  const loadDashboard = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.project !== 'ALL') params.append('project', filters.project);
      if (filters.dateRange !== '7d') params.append('dateRange', filters.dateRange);

      const response = await fetch(`/api/jira/dashboard?${params}`);
      if (response.ok) {
        const data = await response.json();
        setDashboardData(data);
      }
    } catch (error) {
      console.error('Failed to load dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  const searchTickets = async () => {
    if (!searchQuery.trim()) return;

    setLoading(true);
    try {
      const response = await fetch(`/api/jira/search?query=${encodeURIComponent(searchQuery)}&max_results=20`);
      if (response.ok) {
        const data = await response.json();
        setTickets(data.tickets);
      }
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const analyzeTicket = async (ticketKey) => {
    setAnalyzingTicket(ticketKey);
    try {
      const result = await jiraAPI.analyzeTicket(ticketKey);
      console.log('AI Analysis Result:', result);
      setAiAnalysis(result);
    } catch (error) {
      console.error('Analysis failed:', error);
    } finally {
      setAnalyzingTicket(null);
    }
  };

  return (
    <div className="h-full bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 shadow-sm border-b dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-3">
              <ExternalLink className="w-8 h-8 text-blue-600" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">JIRA Integration</h1>
                <p className="text-sm text-gray-500 dark:text-gray-400">Manage tickets and view analytics</p>
              </div>
            </div>

            {/* Tabs */}
            <div className="flex space-x-1 bg-gray-100 dark:bg-gray-700 p-1 rounded-lg">
              <button
                onClick={() => setActiveTab('dashboard')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === 'dashboard'
                  ? 'bg-white dark:bg-gray-600 text-blue-600 dark:text-blue-400 shadow-sm'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                  }`}
              >
                <BarChart3 size={16} className="inline mr-2" />
                Dashboard
              </button>
              <button
                onClick={() => setActiveTab('search')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === 'search'
                  ? 'bg-white dark:bg-gray-600 text-blue-600 dark:text-blue-400 shadow-sm'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                  }`}
              >
                <Search size={16} className="inline mr-2" />
                Search
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex-1 overflow-y-auto bg-gray-50 dark:bg-gray-900">

        {/* Dashboard Tab */}
        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            {/* Filters */}
            <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow-sm">
              <div className="flex items-center space-x-4">
                <Filter size={16} className="text-gray-500 dark:text-gray-400" />
                <select
                  value={filters.project}
                  onChange={(e) => setFilters({ ...filters, project: e.target.value })}
                  className="px-3 py-1 border dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded text-sm"
                >
                  <option value="ALL">All Projects</option>
                  <option value="MBSL3">MBSL3</option>
                  <option value="UNO">UNO</option>
                </select>
                <select
                  value={filters.dateRange}
                  onChange={(e) => setFilters({ ...filters, dateRange: e.target.value })}
                  className="px-3 py-1 border dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded text-sm"
                >
                  <option value="7d">Last 7 days</option>
                  <option value="30d">Last 30 days</option>
                </select>
                <button
                  onClick={loadDashboard}
                  className="px-4 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
                >
                  Refresh
                </button>
              </div>
            </div>

            {loading ? (
              <div className="text-center py-12">Loading dashboard...</div>
            ) : dashboardData?.error ? (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <div className="flex items-center">
                  <AlertCircle className="w-5 h-5 text-red-500 mr-2" />
                  <span className="text-red-700">{dashboardData.error}</span>
                </div>
              </div>
            ) : dashboardData ? (
              <>
                {/* Summary Cards */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border-l-4 border-blue-500">
                    <div className="flex items-center">
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-600 dark:text-gray-400">MBSL3 Open</p>
                        <p className="text-3xl font-bold text-blue-600 dark:text-blue-400">{dashboardData.summary?.mbsl3_open || 0}</p>
                      </div>
                      <BarChart3 className="w-8 h-8 text-blue-500" />
                    </div>
                  </div>

                  <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border-l-4 border-green-500">
                    <div className="flex items-center">
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-600 dark:text-gray-400">UNO Open</p>
                        <p className="text-3xl font-bold text-green-600 dark:text-green-400">{dashboardData.summary?.uno_open || 0}</p>
                      </div>
                      <BarChart3 className="w-8 h-8 text-green-500" />
                    </div>
                  </div>

                  <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border-l-4 border-orange-500">
                    <div className="flex items-center">
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Recent Updates</p>
                        <p className="text-3xl font-bold text-orange-600 dark:text-orange-400">{dashboardData.summary?.recent_updates || 0}</p>
                      </div>
                      <Calendar className="w-8 h-8 text-orange-500" />
                    </div>
                  </div>
                </div>

                {/* Recent Activity (component) */}
                <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm">
                  <RecentActivity projectKey="MBSL3" limit={20} autoRefreshMs={60000} compact />
                </div>
              </>
            ) : (
              <div className="text-center py-12 text-gray-500">No dashboard data available</div>
            )}
          </div>
        )}

        {/* Search Tab */}
        {activeTab === 'search' && (
          <div className="space-y-6">
            <LiveJiraSearch />
            {/* Legacy search panel below (optional retain) */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
              <div className="flex gap-4 mb-6">
                <input
                  type="text"
                  placeholder="Search tickets (e.g., MBSL3, UNO, MBSL3-1234)..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && searchTickets()}
                  className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                <button
                  onClick={searchTickets}
                  disabled={loading}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center"
                >
                  <Search size={16} className="mr-2" />
                  Search
                </button>
              </div>

              {loading ? (
                <div className="text-center py-8">Searching...</div>
              ) : (
                <div className="space-y-2">
                  {tickets.map((ticket) => (
                    <div key={ticket.key} className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-700 rounded hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2">
                          <span className="font-medium text-blue-600 dark:text-blue-400 text-sm">{ticket.key}</span>
                          <span className="text-xs text-gray-500 dark:text-gray-400">• {ticket.assignee}</span>
                          <span className={`px-2 py-1 text-xs rounded-full ${ticket.status === 'Done' ? 'bg-green-100 text-green-800' :
                            ticket.status === 'In Progress' ? 'bg-blue-100 text-blue-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                            {ticket.status}
                          </span>
                        </div>
                        <p className="text-xs text-gray-600 dark:text-gray-300 truncate mt-1">{ticket.summary}</p>
                      </div>
                      <div className="flex items-center space-x-1">
                        {!['Done', 'Closed', 'Rejected', 'Resolved'].includes(ticket.status) && (
                          <button
                            onClick={() => analyzeTicket(ticket.key)}
                            disabled={analyzingTicket === ticket.key}
                            className="p-1 text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 disabled:opacity-50"
                            title="AI Analysis"
                          >
                            {analyzingTicket === ticket.key ? (
                              <Clock size={12} className="animate-spin text-orange-500" />
                            ) : (
                              <Brain size={12} />
                            )}
                          </button>
                        )}
                        <a
                          href={ticket.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-400"
                        >
                          <ExternalLink size={12} />
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* AI Analysis Modal */}
      {aiAnalysis && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg w-full max-w-5xl h-5/6 flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b dark:border-gray-700 flex-shrink-0">
              <div className="flex items-center space-x-3">
                <Brain className="w-6 h-6 text-purple-600" />
                <div>
                  <h2 className="text-lg font-semibold dark:text-white">AI Analysis: {aiAnalysis.ticket_key}</h2>
                  <p className="text-sm text-gray-500 dark:text-gray-400 truncate">{aiAnalysis.ticket_info?.summary}</p>
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
                      <span className={`ml-2 px-2 py-1 rounded-full text-xs ${aiAnalysis.ticket_info?.status === 'Done' ? 'bg-green-100 text-green-800' :
                        aiAnalysis.ticket_info?.status === 'In Progress' ? 'bg-blue-100 text-blue-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                        {aiAnalysis.ticket_info?.status}
                      </span>
                    </div>
                    <div>
                      <span className="font-medium text-gray-600 dark:text-gray-400">Assignee:</span>
                      <span className="ml-2 dark:text-gray-300">{aiAnalysis.ticket_info?.assignee}</span>
                    </div>
                  </div>

                  <div className="mt-4">
                    <a
                      href={aiAnalysis.ticket_info?.url}
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
                    AI Recommendations
                  </h3>
                  <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 h-96 overflow-y-auto">
                    <div className="space-y-3">
                      {aiAnalysis.ai_analysis.split('\n\n').map((section, index) => {
                        if (section.includes('###')) {
                          const [title, ...content] = section.split('\n');
                          return (
                            <div key={index} className="mb-4">
                              <h4 className="font-semibold text-purple-700 dark:text-purple-300 mb-2">
                                {title.replace('###', '').trim()}
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
                          <p key={index} className="text-gray-700 dark:text-gray-300 text-sm">
                            {section.replace(/\*\*/g, '')}
                          </p>
                        );
                      })}
                    </div>
                  </div>

                  <div className="mt-3 flex items-center space-x-4 text-xs text-gray-500 dark:text-gray-400">
                    <div className="flex items-center space-x-1">
                      <Clock size={12} />
                      <span>Generated just now</span>
                    </div>
                    <div className="flex items-center space-x-1">
                      <Brain size={12} />
                      <span>Powered by Groq AI</span>
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

export default JiraPage;