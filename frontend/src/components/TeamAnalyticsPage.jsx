import React, { useState, useEffect, useMemo } from 'react';
import { Users, TrendingUp, Clock, AlertTriangle, CheckCircle, XCircle, Pause, Play, Brain, BarChart3, User, Calendar, Target, Zap, Activity } from 'lucide-react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';

const TeamAnalyticsPage = () => {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selectedMember, setSelectedMember] = useState(null);
  const [individualAnalysis, setIndividualAnalysis] = useState(null);
  const [dateRange, setDateRange] = useState('30d');

  const colorThemes = {
    blue: {
      border: 'border-blue-500',
      value: 'text-blue-600 dark:text-blue-400',
      iconBg: 'bg-blue-100 dark:bg-blue-900/20',
      icon: 'text-blue-600 dark:text-blue-400'
    },
    green: {
      border: 'border-green-500',
      value: 'text-green-600 dark:text-green-400',
      iconBg: 'bg-green-100 dark:bg-green-900/20',
      icon: 'text-green-600 dark:text-green-400'
    },
    purple: {
      border: 'border-purple-500',
      value: 'text-purple-600 dark:text-purple-400',
      iconBg: 'bg-purple-100 dark:bg-purple-900/20',
      icon: 'text-purple-600 dark:text-purple-400'
    },
    orange: {
      border: 'border-orange-500',
      value: 'text-orange-600 dark:text-orange-400',
      iconBg: 'bg-orange-100 dark:bg-orange-900/20',
      icon: 'text-orange-600 dark:text-orange-400'
    },
    red: {
      border: 'border-red-500',
      value: 'text-red-600 dark:text-red-400',
      iconBg: 'bg-red-100 dark:bg-red-900/20',
      icon: 'text-red-600 dark:text-red-400'
    },
    cyan: {
      border: 'border-cyan-500',
      value: 'text-cyan-600 dark:text-cyan-300',
      iconBg: 'bg-cyan-100 dark:bg-cyan-900/20',
      icon: 'text-cyan-600 dark:text-cyan-300'
    },
    pink: {
      border: 'border-pink-500',
      value: 'text-pink-600 dark:text-pink-300',
      iconBg: 'bg-pink-100 dark:bg-pink-900/20',
      icon: 'text-pink-600 dark:text-pink-300'
    }
  };

  const getColorTheme = (color) => colorThemes[color] || colorThemes.blue;

  const confidenceThemes = {
    high: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-200',
    medium: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-200',
    low: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-200'
  };

  const getConfidenceBadge = (confidence) => confidenceThemes[confidence] || confidenceThemes.low;

  const trendThemes = {
    increasing: 'text-red-600 dark:text-red-300',
    decreasing: 'text-green-600 dark:text-green-300',
    stable: 'text-blue-600 dark:text-blue-300'
  };

  const getTrendClass = (trend) => trendThemes[trend] || trendThemes.stable;

  const signalThemes = {
    forecast: {
      border: 'border-cyan-500',
      bg: 'bg-cyan-50 dark:bg-cyan-900/20',
      text: 'text-cyan-700 dark:text-cyan-200'
    },
    info: {
      border: 'border-blue-500',
      bg: 'bg-blue-50 dark:bg-blue-900/20',
      text: 'text-blue-700 dark:text-blue-200'
    },
    warning: {
      border: 'border-yellow-500',
      bg: 'bg-yellow-50 dark:bg-yellow-900/20',
      text: 'text-yellow-700 dark:text-yellow-200'
    },
    critical: {
      border: 'border-red-500',
      bg: 'bg-red-50 dark:bg-red-900/20',
      text: 'text-red-700 dark:text-red-200'
    }
  };

  const getSignalTheme = (type) => signalThemes[type] || signalThemes.info;

  const formatNumber = (value, options = {}) => {
    if (value === null || value === undefined || value === '') return '-';
    const numeric = Number(value);
    if (Number.isNaN(numeric)) return '-';
    return numeric.toLocaleString(undefined, options);
  };

  const humanize = (value) => {
    if (!value || typeof value !== 'string') return '';
    return value.charAt(0).toUpperCase() + value.slice(1);
  };

  const renderSummaryIcon = (title, iconClass) => {
    if (title === 'Team Members') return <Users className={`w-6 h-6 ${iconClass}`} />;
    if (title === 'Total Tickets') return <Target className={`w-6 h-6 ${iconClass}`} />;
    if (title === 'Avg Completion') return <CheckCircle className={`w-6 h-6 ${iconClass}`} />;
    if (title === 'Avg Resolution') return <Clock className={`w-6 h-6 ${iconClass}`} />;
    if (title === 'High Priority Open') return <AlertTriangle className={`w-6 h-6 ${iconClass}`} />;
    if (title === 'Projected New (7d)') return <Calendar className={`w-6 h-6 ${iconClass}`} />;
    if (title === 'Effort (hrs, 7d)') return <Zap className={`w-6 h-6 ${iconClass}`} />;
    return <BarChart3 className={`w-6 h-6 ${iconClass}`} />;
  };

  const throughputTooltipContent = ({ active, payload, label }) => {
    if (!active || !payload || payload.length === 0) return null;
    return (
      <div className="bg-white dark:bg-gray-800 p-3 rounded-lg shadow border border-gray-200 dark:border-gray-700">
        <p className="text-xs font-semibold text-gray-700 dark:text-gray-200">{label}</p>
        {payload.map((item) => (
          <div key={item.dataKey} className="text-xs text-gray-600 dark:text-gray-300 mt-1">
            <span className="font-medium" style={{ color: item.color }}>
              {humanize(item.dataKey)}
            </span>
            : {formatNumber(item.value)}
          </div>
        ))}
      </div>
    );
  };

  const throughputData = useMemo(() => {
    if (!analytics?.trend_metrics?.daily_throughput) return [];
    return analytics.trend_metrics.daily_throughput.map((entry) => {
      let label = entry.date;
      try {
        label = new Date(entry.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
      } catch (error) {
        // ignore parse errors and fall back to raw value
      }
      return {
        ...entry,
        label,
        created: entry.created ?? 0,
        resolved: entry.resolved ?? 0
      };
    });
  }, [analytics]);

  const throughputSummary = useMemo(() => {
    if (!throughputData.length) return null;
    const totalCreated = throughputData.reduce((sum, item) => sum + (item.created || 0), 0);
    const totalResolved = throughputData.reduce((sum, item) => sum + (item.resolved || 0), 0);
    const netDelta = totalCreated - totalResolved;
    const netTrend = netDelta > 0 ? 'increasing' : netDelta < 0 ? 'decreasing' : 'stable';

    return {
      totalCreated,
      totalResolved,
      netDelta,
      netTrend,
      averageCreated: totalCreated / throughputData.length,
      averageResolved: totalResolved / throughputData.length
    };
  }, [throughputData]);

  useEffect(() => {
    loadTeamAnalytics();
  }, [dateRange]);

  const loadTeamAnalytics = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/jira/team-analytics?date_range=${dateRange}`);
      const data = await response.json();
      if (response.ok) {
        setAnalytics(data);
      }
    } catch (error) {
      console.error('Failed to load team analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadIndividualAnalysis = async (assignee) => {
    try {
      const response = await fetch(`/api/jira/individual-analysis/${encodeURIComponent(assignee)}?date_range=${dateRange}`);
      const data = await response.json();
      if (response.ok) {
        setIndividualAnalysis(data);
        setSelectedMember(assignee);
      }
    } catch (error) {
      console.error('Failed to load individual analysis:', error);
    }
  };

  const getStatusIcon = (status) => {
    const statusLower = status.toLowerCase();
    if (statusLower.includes('done') || statusLower.includes('closed')) return <CheckCircle className="w-4 h-4 text-green-500" />;
    if (statusLower.includes('progress')) return <Play className="w-4 h-4 text-blue-500" />;
    if (statusLower.includes('reject')) return <XCircle className="w-4 h-4 text-red-500" />;
    if (statusLower.includes('hold')) return <Pause className="w-4 h-4 text-yellow-500" />;
    return <Clock className="w-4 h-4 text-gray-500" />;
  };

  const getPerformanceColor = (score) => {
    if (score >= 80) return 'text-green-600 bg-green-100';
    if (score >= 60) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  const getTrendIcon = (trend) => {
    if (trend === 'improving') return <TrendingUp className="w-4 h-4 text-green-500" />;
    if (trend === 'declining') return <AlertTriangle className="w-4 h-4 text-red-500" />;
    return <BarChart3 className="w-4 h-4 text-gray-500" />;
  };

  if (loading) {
    return (
      <div className="h-full bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600 dark:text-gray-400">Loading team analytics...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 shadow-sm border-b dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-3">
              <Users className="w-8 h-8 text-blue-600" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Team Analytics</h1>
                <p className="text-sm text-gray-500 dark:text-gray-400">AI-powered productivity insights</p>
              </div>
            </div>
            
            <select 
              value={dateRange}
              onChange={(e) => setDateRange(e.target.value)}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg"
            >
              <option value="7d">Last 7 days</option>
              <option value="30d">Last 30 days</option>
              <option value="90d">Last 90 days</option>
            </select>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {analytics && (
          <>
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
              {analytics.summary_cards?.map((card, index) => {
                const theme = getColorTheme(card.color);
                return (
                  <div key={index} className={`bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border-l-4 ${theme.border}`}>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-600 dark:text-gray-400">{card.title}</p>
                        <p className={`text-3xl font-bold ${theme.value}`}>
                          {card.value}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">{card.subtitle}</p>
                      </div>
                      <div className={`p-3 rounded-full ${theme.iconBg}`}>
                        {renderSummaryIcon(card.title, theme.icon)}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Team Performance Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
              {/* Individual Performance Cards */}
              <div className="lg:col-span-2">
                <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
                  <h3 className="text-lg font-semibold mb-4 dark:text-white flex items-center">
                    <User className="w-5 h-5 mr-2 text-blue-600" />
                    Individual Performance
                  </h3>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {analytics.individual_performance?.map((person, index) => (
                      <div 
                        key={index}
                        onClick={() => loadIndividualAnalysis(person.assignee)}
                        className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer transition-colors"
                      >
                        <div className="flex items-center justify-between mb-3">
                          <h4 className="font-medium text-gray-900 dark:text-white truncate">
                            {person.assignee}
                          </h4>
                          <div className={`px-2 py-1 rounded-full text-xs font-medium ${getPerformanceColor(person.productivity_score)}`}>
                            {person.productivity_score}
                          </div>
                        </div>
                        
                        <div className="grid grid-cols-3 gap-2 text-xs">
                          <div className="text-center">
                            <div className="flex items-center justify-center mb-1">
                              <CheckCircle className="w-3 h-3 text-green-500 mr-1" />
                              <span className="font-medium">{person.metrics.done}</span>
                            </div>
                            <p className="text-gray-500">Done</p>
                          </div>
                          <div className="text-center">
                            <div className="flex items-center justify-center mb-1">
                              <Play className="w-3 h-3 text-blue-500 mr-1" />
                              <span className="font-medium">{person.metrics.in_progress}</span>
                            </div>
                            <p className="text-gray-500">In Progress</p>
                          </div>
                          <div className="text-center">
                            <div className="flex items-center justify-center mb-1">
                              <Clock className="w-3 h-3 text-gray-500 mr-1" />
                              <span className="font-medium">{person.metrics.todo}</span>
                            </div>
                            <p className="text-gray-500">To Do</p>
                          </div>
                        </div>
                        
                        <div className="mt-3 flex items-center justify-between text-xs">
                          <span className="text-gray-500">Completion: {person.completion_rate}%</span>
                          <div className="flex items-center">
                            {getTrendIcon(person.performance_trend)}
                            <span className="ml-1 text-gray-500">{person.performance_trend}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Forecast & Insights */}
              <div className="lg:col-span-1">
                <div className="space-y-4">
                  {analytics.ai_forecast && (
                    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
                      <h3 className="text-lg font-semibold mb-4 dark:text-white flex items-center">
                        <Brain className="w-5 h-5 mr-2 text-purple-600" />
                        AI Workload Forecast
                      </h3>
                      <div className="flex items-center justify-between mb-4">
                        <span className={`text-xs font-medium px-2 py-1 rounded-full ${getConfidenceBadge((analytics.ai_forecast.confidence || 'low').toLowerCase())}`}>
                          Confidence: {humanize((analytics.ai_forecast.confidence || 'low').toLowerCase())}
                        </span>
                        <span className={`text-xs font-medium ${getTrendClass((analytics.ai_forecast.backlog_trend || 'stable').toLowerCase())}`}>
                          Backlog {humanize((analytics.ai_forecast.backlog_trend || 'stable').toLowerCase())}
                        </span>
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <p className="text-xs text-gray-500 dark:text-gray-400">Projected new (7d)</p>
                          <p className="text-2xl font-semibold text-blue-600 dark:text-blue-300">
                            {formatNumber(analytics.ai_forecast.projected_new_tickets)}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-500 dark:text-gray-400">Projected completed (7d)</p>
                          <p className="text-2xl font-semibold text-green-600 dark:text-green-300">
                            {formatNumber(analytics.ai_forecast.projected_completed_tickets)}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-500 dark:text-gray-400">Estimated effort (hrs)</p>
                          <p className="text-2xl font-semibold text-purple-600 dark:text-purple-300">
                            {formatNumber(analytics.ai_forecast.estimated_effort_hours, { maximumFractionDigits: 1 })}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-500 dark:text-gray-400">Backlog delta (7d)</p>
                          <p className={`text-2xl font-semibold ${getTrendClass((analytics.ai_forecast.backlog_trend || 'stable').toLowerCase())}`}>
                            {formatNumber(analytics.ai_forecast.backlog_delta_next_7_days)}
                          </p>
                        </div>
                      </div>

                      {analytics.trend_metrics && (
                        <div className="mt-4 border-t border-gray-100 dark:border-gray-700 pt-4">
                          <p className="text-xs font-semibold uppercase text-gray-500 dark:text-gray-400 mb-2">Momentum snapshot</p>
                          <div className="grid grid-cols-2 gap-3 text-sm">
                            <div>
                              <p className="text-gray-500 dark:text-gray-400">Avg created / day</p>
                              <p className="font-semibold text-gray-900 dark:text-white">
                                {formatNumber(analytics.trend_metrics?.avg_created_per_day, { maximumFractionDigits: 2 })}
                              </p>
                            </div>
                            <div>
                              <p className="text-gray-500 dark:text-gray-400">Avg resolved / day</p>
                              <p className="font-semibold text-gray-900 dark:text-white">
                                {formatNumber(analytics.trend_metrics?.avg_resolved_per_day, { maximumFractionDigits: 2 })}
                              </p>
                            </div>
                            <div>
                              <p className="text-gray-500 dark:text-gray-400">Created last 7d</p>
                              <p className="font-semibold text-gray-900 dark:text-white">
                                {formatNumber(analytics.trend_metrics?.created_last_7_days)}
                              </p>
                            </div>
                            <div>
                              <p className="text-gray-500 dark:text-gray-400">Resolved last 7d</p>
                              <p className="font-semibold text-gray-900 dark:text-white">
                                {formatNumber(analytics.trend_metrics?.resolved_last_7_days)}
                              </p>
                            </div>
                            {typeof analytics.trend_metrics?.throughput_ratio === 'number' && (
                              <div>
                                <p className="text-gray-500 dark:text-gray-400">Throughput ratio</p>
                                <p className="font-semibold text-gray-900 dark:text-white">
                                  {formatNumber(analytics.trend_metrics.throughput_ratio, { maximumFractionDigits: 2 })}
                                </p>
                              </div>
                            )}
                          </div>
                          {typeof analytics.trend_metrics?.observation_window_days === 'number' && (
                            <p className="text-xs text-gray-500 dark:text-gray-400 mt-3">
                              Observation window: {analytics.trend_metrics.observation_window_days} days
                            </p>
                          )}
                        </div>
                      )}

                      {analytics.ai_forecast.notes?.length > 0 && (
                        <div className="mt-4 space-y-2">
                          {analytics.ai_forecast.notes.map((note, idx) => (
                            <div key={idx} className="text-xs text-purple-700 dark:text-purple-200 bg-purple-50 dark:bg-purple-900/20 p-2 rounded">
                              {note}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {analytics.team_insights?.length > 0 && (
                    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
                      <h3 className="text-lg font-semibold mb-4 dark:text-white flex items-center">
                        <AlertTriangle className="w-5 h-5 mr-2 text-red-500" />
                        Team Signals
                      </h3>
                      <div className="space-y-3 max-h-64 overflow-y-auto">
                        {analytics.team_insights.map((signal, idx) => {
                          const theme = getSignalTheme(signal.type);
                          return (
                            <div key={idx} className={`p-3 rounded-lg border-l-4 ${theme.border} ${theme.bg}`}>
                              <p className={`text-sm font-semibold ${theme.text}`}>
                                {signal.meta?.title || humanize(signal.type)}
                              </p>
                              <p className={`text-xs mt-1 ${theme.text}`}>
                                {signal.message}
                              </p>
                              {signal.meta?.value !== undefined && (
                                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                                  Current value: {signal.meta.value}
                                </p>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
                    <h3 className="text-lg font-semibold mb-4 dark:text-white flex items-center">
                      <Users className="w-5 h-5 mr-2 text-blue-600" />
                      Personalized Insights
                    </h3>
                    <div className="space-y-4 max-h-72 overflow-y-auto">
                      {analytics.productivity_insights?.map((insight, index) => (
                        <div key={index} className="border-l-4 border-blue-500 pl-4">
                          <h4 className="font-medium text-sm text-gray-900 dark:text-white mb-2">
                            {insight.assignee}
                          </h4>
                          <div className="space-y-2">
                            {insight.insights.map((item, idx) => (
                              <div key={idx} className={`p-2 rounded text-xs ${
                                item.type === 'positive' ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300' :
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
                </div>
              </div>
            </div>
            {/* Daily Throughput Timeline */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6 mb-8">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-2">
                  <Activity className="w-5 h-5 text-teal-600" />
                  <h3 className="text-lg font-semibold dark:text-white">Daily Throughput</h3>
                </div>
                {throughputSummary && (
                  <div className="flex flex-wrap items-center gap-4 text-sm text-gray-600 dark:text-gray-300">
                    <span>
                      Created: <strong className="text-blue-600 dark:text-blue-300">{formatNumber(throughputSummary.totalCreated)}</strong>
                    </span>
                    <span>
                      Resolved: <strong className="text-green-600 dark:text-green-300">{formatNumber(throughputSummary.totalResolved)}</strong>
                    </span>
                    <span className={`font-semibold ${getTrendClass(throughputSummary.netTrend)}`}>
                      Net Δ: {throughputSummary.netDelta > 0 ? '+' : ''}{formatNumber(throughputSummary.netDelta)}
                    </span>
                  </div>
                )}
              </div>
              <div className="h-64">
                {throughputData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={throughputData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                      <defs>
                        <linearGradient id="createdGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.4} />
                          <stop offset="95%" stopColor="#3B82F6" stopOpacity={0.05} />
                        </linearGradient>
                        <linearGradient id="resolvedGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#10B981" stopOpacity={0.45} />
                          <stop offset="95%" stopColor="#10B981" stopOpacity={0.05} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" opacity={0.4} />
                      <XAxis dataKey="label" tick={{ fontSize: 12 }} stroke="#6B7280" />
                      <YAxis allowDecimals={false} tick={{ fontSize: 12 }} stroke="#6B7280" />
                      <Tooltip content={throughputTooltipContent} />
                      <Area type="monotone" dataKey="created" stroke="#3B82F6" fill="url(#createdGradient)" name="created" strokeWidth={2} activeDot={{ r: 4 }} />
                      <Area type="monotone" dataKey="resolved" stroke="#10B981" fill="url(#resolvedGradient)" name="resolved" strokeWidth={2} activeDot={{ r: 4 }} />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-sm text-gray-500 dark:text-gray-400 border border-dashed border-gray-200 dark:border-gray-700 rounded-lg">
                    No throughput history for the selected range.
                  </div>
                )}
              </div>
              {throughputSummary && (
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-4 text-sm text-gray-600 dark:text-gray-300">
                  <div>
                    <p className="uppercase text-xs text-gray-500 dark:text-gray-400">Avg Created / Day</p>
                    <p className="font-semibold text-gray-900 dark:text-white">
                      {formatNumber(throughputSummary.averageCreated, { maximumFractionDigits: 2 })}
                    </p>
                  </div>
                  <div>
                    <p className="uppercase text-xs text-gray-500 dark:text-gray-400">Avg Resolved / Day</p>
                    <p className="font-semibold text-gray-900 dark:text-white">
                      {formatNumber(throughputSummary.averageResolved, { maximumFractionDigits: 2 })}
                    </p>
                  </div>
                  <div>
                    <p className="uppercase text-xs text-gray-500 dark:text-gray-400">Trend</p>
                    <p className={`font-semibold ${getTrendClass(throughputSummary.netTrend)}`}>
                      {humanize(throughputSummary.netTrend)}
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Team Overview Charts */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Status Distribution */}
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
                <h3 className="text-lg font-semibold mb-4 dark:text-white">Status Distribution</h3>
                <div className="space-y-3">
                  {Object.entries(analytics.team_overview?.status_distribution || {}).slice(0, 6).map(([status, count]) => (
                    <div key={status} className="flex items-center justify-between">
                      <div className="flex items-center">
                        {getStatusIcon(status)}
                        <span className="ml-2 text-sm text-gray-600 dark:text-gray-400">{status}</span>
                      </div>
                      <span className="font-medium dark:text-white">{count}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Priority Distribution */}
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
                <h3 className="text-lg font-semibold mb-4 dark:text-white">Priority Breakdown</h3>
                <div className="space-y-3">
                  {Object.entries(analytics.team_overview?.priority_distribution || {}).map(([priority, count]) => (
                    <div key={priority} className="flex items-center justify-between">
                      <div className="flex items-center">
                        <div className={`w-3 h-3 rounded-full mr-2 ${
                          priority === 'High' ? 'bg-red-500' :
                          priority === 'Medium' ? 'bg-yellow-500' :
                          priority === 'Low' ? 'bg-green-500' :
                          'bg-gray-500'
                        }`}></div>
                        <span className="text-sm text-gray-600 dark:text-gray-400">{priority}</span>
                      </div>
                      <span className="font-medium dark:text-white">{count}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Type Distribution */}
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
                <h3 className="text-lg font-semibold mb-4 dark:text-white">Issue Types</h3>
                <div className="space-y-3">
                  {Object.entries(analytics.team_overview?.type_distribution || {}).map(([type, count]) => (
                    <div key={type} className="flex items-center justify-between">
                      <div className="flex items-center">
                        <div className={`w-3 h-3 rounded-full mr-2 ${
                          type === 'Bug' ? 'bg-red-500' :
                          type === 'Story' ? 'bg-blue-500' :
                          type === 'Task' ? 'bg-green-500' :
                          'bg-purple-500'
                        }`}></div>
                        <span className="text-sm text-gray-600 dark:text-gray-400">{type}</span>
                      </div>
                      <span className="font-medium dark:text-white">{count}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </>
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
                onClick={() => {setSelectedMember(null); setIndividualAnalysis(null);}}
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
                            <span className={`px-2 py-1 text-xs rounded-full ${
                              ticket.status === 'Done' ? 'bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200' :
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
    </div>
  );
};

export default TeamAnalyticsPage;
