import {
  AlertCircle,
  BarChart3,
  Brain,
  CheckCircle,
  Clock,
  ExternalLink,
  Loader2,
  Play,
  RefreshCw,
  Target,
  TrendingUp,
  User,
  Users,
  XCircle
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { jiraAPI } from '../services/api';
import {
  InteractiveList,
  MetricCard,
  PriorityRadialChart,
  StatusDistributionChart,
  TeamPerformanceChart
} from './Charts/EnhancedCharts';
import LiveJiraSearch from './LiveJiraSearch';
import RecentActivity from './RecentActivity';

const EnhancedJiraDashboard = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [dashboardData, setDashboardData] = useState(null);
  const [teamAnalytics, setTeamAnalytics] = useState(null);
  const [loading, setLoading] = useState(false);
  const [dateRange, setDateRange] = useState('30d');
  const [selectedMember, setSelectedMember] = useState(null);
  const [memberDetails, setMemberDetails] = useState(null);
  const [showMemberModal, setShowMemberModal] = useState(false);

  useEffect(() => {
    if (activeTab === 'dashboard') {
      loadDashboard();
    } else if (activeTab === 'analytics') {
      loadTeamAnalytics();
    }
  }, [activeTab, dateRange]);

  const loadDashboard = async () => {
    setLoading(true);
    try {
      const data = await jiraAPI.getLiveSummary(dateRange);
      // Transform live summary -> expected dashboardData shape
      const transformed = {
        summary: {
          total_tickets: data.total,
          active_tickets: data.active,
          resolved_tickets: data.resolved,
          active_percentage: data.active_pct,
          resolved_percentage: data.resolved_pct
        },
        status_distribution: data.status_distribution || {},
        priority_distribution: data.priority_distribution || {},
        assignee_distribution: Object.fromEntries((data.assignee_top || []).map(([n, c]) => [n, c])),
        type_distribution: {},
        recent_tickets: []
      };
      setDashboardData(transformed);
    } catch (error) {
      console.error('Failed to load live summary:', error);
    } finally { setLoading(false); }
  };

  const loadTeamAnalytics = async () => {
    setLoading(true);
    try {
      const team = await jiraAPI.getLiveTeam();
      const cards = (team.cards || []).map(c => ({
        assignee: c.assignee,
        metrics: { done: c.done, in_progress: c.progress, todo: c.todo },
        completion_rate: c.completion_pct,
        productivity_score: c.completion_pct,
        performance_trend: 'stable'
      }));
      const transformed = {
        summary_cards: [
          { title: 'Team Members', value: team.team_members, subtitle: 'Active', color: 'blue' },
          { title: 'Avg Completion', value: cards.length ? Math.round(cards.reduce((a, b) => a + b.completion_rate, 0) / cards.length) : 0, subtitle: 'Avg %', color: 'green' },
          { title: 'Total Tickets', value: dashboardData?.summary?.total_tickets || '-', subtitle: 'From summary', color: 'purple' },
        ],
        individual_performance: cards,
        productivity_insights: []
      };
      setTeamAnalytics(transformed);
    } catch (e) { console.error('Failed to load live team:', e); } finally { setLoading(false); }
  };

  const handleMemberClick = async (member) => {
    setSelectedMember(member);
    try {
      const data = await jiraAPI.getMemberDetails(member.assignee);
      setMemberDetails(data);
      setShowMemberModal(true);
    } catch (error) {
      console.error('Failed to load member details:', error);
    }
  };

  const handleStatusClick = (status) => {
    console.log('Status clicked:', status);
    // Navigate to filtered view or show details
  };

  const handleAssigneeClick = (assignee) => {
    console.log('Assignee clicked:', assignee);
    // Show assignee details or navigate to their tickets
  };

  if (loading && !dashboardData && activeTab === 'dashboard') {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin mx-auto text-blue-600 mb-4" />
          <p className="text-gray-600 dark:text-gray-400">Loading live JIRA summary...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 shadow-sm border-b dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-blue-100 dark:bg-blue-900/20 rounded-lg">
                <BarChart3 className="w-8 h-8 text-blue-600" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">JIRA Analytics Hub</h1>
                <p className="text-sm text-gray-500 dark:text-gray-400">Enhanced insights and team performance</p>
              </div>
            </div>

            <div className="flex items-center space-x-4">
              {/* Date Range Selector */}
              <select
                value={dateRange}
                onChange={(e) => setDateRange(e.target.value)}
                className="px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg text-sm"
              >
                <option value="7d">Last 7 days</option>
                <option value="30d">Last 30 days</option>
                <option value="90d">Last 90 days</option>
              </select>

              {/* Refresh Button */}
              <button
                onClick={() => activeTab === 'dashboard' ? loadDashboard() : loadTeamAnalytics()}
                className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
              >
                <RefreshCw className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex space-x-1 bg-gray-100 dark:bg-gray-700 p-1 rounded-lg mb-4 w-fit">
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors flex items-center space-x-2 ${activeTab === 'dashboard'
                ? 'bg-white dark:bg-gray-600 text-blue-600 dark:text-blue-400 shadow-sm'
                : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                }`}
            >
              <BarChart3 size={16} />
              <span>Dashboard</span>
            </button>
            <button
              onClick={() => setActiveTab('analytics')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors flex items-center space-x-2 ${activeTab === 'analytics'
                ? 'bg-white dark:bg-gray-600 text-blue-600 dark:text-blue-400 shadow-sm'
                : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                }`}
            >
              <Users size={16} />
              <span>Team Analytics</span>
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">

        {/* Dashboard Tab */}
        {activeTab === 'dashboard' && dashboardData && (
          <div className="space-y-6">
            {/* Empty state */}
            {!loading && dashboardData.summary?.total_tickets === 0 && (
              <div className="p-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 text-center text-sm text-gray-600 dark:text-gray-300">
                No tickets found in selected range.
              </div>)}
            {/* Key Metrics Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <MetricCard
                title="Total Tickets"
                value={dashboardData.summary?.total_tickets || 0}
                subtitle="All time"
                icon={Target}
                color="blue"
                clickable={true}
                onClick={() => console.log('Total tickets clicked')}
              />
              <MetricCard
                title="Active Tickets"
                value={dashboardData.summary?.active_tickets || 0}
                subtitle={`${dashboardData.summary?.active_percentage || 0}% of total`}
                icon={Play}
                color="green"
                trend={5}
                clickable={true}
                onClick={() => console.log('Active tickets clicked')}
              />
              <MetricCard
                title="Resolved"
                value={dashboardData.summary?.resolved_tickets || 0}
                subtitle={`${dashboardData.summary?.resolved_percentage || 0}% completion`}
                icon={CheckCircle}
                color="purple"
                trend={-2}
                clickable={true}
                onClick={() => console.log('Resolved tickets clicked')}
              />
              <MetricCard
                title="Team Members"
                value={Object.keys(dashboardData.assignee_distribution || {}).length}
                subtitle="Active contributors"
                icon={Users}
                color="orange"
                clickable={true}
                onClick={() => setActiveTab('analytics')}
              />
            </div>

            {/* Charts Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Status Distribution */}
              <StatusDistributionChart
                data={dashboardData.status_distribution}
                onSegmentClick={handleStatusClick}
              />

              {/* Priority Distribution */}
              <PriorityRadialChart
                data={dashboardData.priority_distribution}
              />
            </div>

            {/* Lists Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Top Assignees */}
              <InteractiveList
                title="Top Assignees"
                icon={Users}
                color="blue"
                items={Object.entries(dashboardData.assignee_distribution || {})
                  .slice(0, 8)
                  .map(([name, count]) => ({
                    name,
                    value: count,
                    subtitle: `${count} tickets assigned`
                  }))}
                onItemClick={handleAssigneeClick}
              />

              {/* Issue Types */}
              <InteractiveList
                title="Issue Types"
                icon={Target}
                color="purple"
                items={Object.entries(dashboardData.type_distribution || {})
                  .slice(0, 8)
                  .map(([type, count]) => ({
                    name: type,
                    value: count,
                    subtitle: `${((count / dashboardData.summary?.total_tickets) * 100).toFixed(1)}% of total`
                  }))}
                onItemClick={(item) => console.log('Type clicked:', item)}
              />

              {/* Recent Activity (full component) */}
              <div className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm border border-gray-200 dark:border-gray-700">
                <RecentActivity projectKey="MBSL3" limit={15} autoRefreshMs={60000} compact />
              </div>
            </div>

            {/* Live Search Block */}
            <LiveJiraSearch />
          </div>
        )}

        {/* Analytics Tab */}
        {activeTab === 'analytics' && teamAnalytics && (
          <div className="space-y-6">
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              {teamAnalytics.summary_cards?.map((card, index) => (
                <MetricCard
                  key={index}
                  title={card.title}
                  value={card.value}
                  subtitle={card.subtitle}
                  icon={card.title === 'Team Members' ? Users :
                    card.title === 'Total Tickets' ? Target :
                      card.title === 'Avg Completion' ? CheckCircle : Clock}
                  color={card.color}
                  clickable={true}
                />
              ))}
            </div>

            {/* Team Performance Chart */}
            <TeamPerformanceChart
              data={teamAnalytics.individual_performance}
              onBarClick={handleMemberClick}
            />

            {/* Performance Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Individual Performance Cards */}
              <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
                  <User className="w-5 h-5 mr-2 text-blue-600" />
                  Team Members
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-h-96 overflow-y-auto">
                  {teamAnalytics.individual_performance?.map((person, index) => (
                    <div
                      key={index}
                      onClick={() => handleMemberClick(person)}
                      className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer transition-all duration-200 hover:shadow-md"
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
                        <span className="text-gray-500 dark:text-gray-400">
                          Completion: {person.completion_rate}%
                        </span>
                        <div className="flex items-center">
                          {person.performance_trend === 'improving' && <TrendingUp className="w-3 h-3 text-green-500" />}
                          {person.performance_trend === 'declining' && <AlertCircle className="w-3 h-3 text-red-500" />}
                          {person.performance_trend === 'stable' && <BarChart3 className="w-3 h-3 text-gray-500" />}
                          <span className="ml-1 text-gray-500 dark:text-gray-400 capitalize">
                            {person.performance_trend}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* AI Insights */}
              <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
                  <Brain className="w-5 h-5 mr-2 text-purple-600" />
                  AI Productivity Insights
                </h3>

                <div className="space-y-4 max-h-96 overflow-y-auto">
                  {teamAnalytics.productivity_insights?.map((insight, index) => (
                    <div key={index} className="border-l-4 border-purple-500 pl-4 py-2">
                      <h4 className="font-medium text-sm text-gray-900 dark:text-white mb-2">
                        {insight.assignee}
                      </h4>
                      <div className="space-y-2">
                        {insight.insights.map((item, idx) => (
                          <div key={idx} className={`p-3 rounded-lg text-sm ${item.type === 'positive' ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 border border-green-200 dark:border-green-800' :
                            item.type === 'concern' ? 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800' :
                              item.type === 'warning' ? 'bg-yellow-50 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-300 border border-yellow-200 dark:border-yellow-800' :
                                'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800'
                            }`}>
                            {item.message}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Member Details Modal */}
      {showMemberModal && selectedMember && memberDetails && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl w-full max-w-4xl h-5/6 flex flex-col shadow-2xl">
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b dark:border-gray-700">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-blue-100 dark:bg-blue-900/20 rounded-lg">
                  <User className="w-6 h-6 text-blue-600" />
                </div>
                <div>
                  <h2 className="text-xl font-semibold dark:text-white">{selectedMember.assignee}</h2>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Individual Performance Analysis</p>
                </div>
              </div>
              <button
                onClick={() => setShowMemberModal(false)}
                className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
              >
                <XCircle className="w-6 h-6" />
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6">
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Performance Summary */}
                <div className="lg:col-span-1 space-y-4">
                  <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                    <h3 className="font-semibold mb-3 dark:text-white">Performance Summary</h3>
                    {memberDetails.performance_summary && (
                      <div className="space-y-3">
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600 dark:text-gray-400">Completion Rate:</span>
                          <span className="font-medium dark:text-white">
                            {memberDetails.performance_summary.completion_rate}%
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600 dark:text-gray-400">Avg Resolution:</span>
                          <span className="font-medium dark:text-white">
                            {memberDetails.performance_summary.avg_resolution_days} days
                          </span>
                        </div>
                        <div className="mt-4">
                          <h4 className="text-sm font-medium mb-2 dark:text-white">Status Breakdown:</h4>
                          {Object.entries(memberDetails.performance_summary.status_breakdown || {}).map(([status, count]) => (
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
                  <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4 border border-purple-200 dark:border-purple-800">
                    <h3 className="font-semibold mb-3 text-purple-800 dark:text-purple-300 flex items-center">
                      <Brain className="w-4 h-4 mr-2" />
                      AI Insights
                    </h3>
                    <div className="space-y-2">
                      {memberDetails.performance_summary?.productivity_insights?.map((insight, idx) => (
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
                    {memberDetails.status_timeline?.slice(0, 20).map((ticket, idx) => (
                      <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors">
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
                        <a
                          href={ticket.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="p-2 text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-400 rounded"
                        >
                          <ExternalLink className="w-4 h-4" />
                        </a>
                      </div>
                    ))}
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

export default EnhancedJiraDashboard;