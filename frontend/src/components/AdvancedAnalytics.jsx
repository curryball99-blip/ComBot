import React, { useState, useEffect } from 'react';
import { 
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, 
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  AreaChart, Area, RadialBarChart, RadialBar, ComposedChart,
  ScatterChart, Scatter, Treemap
} from 'recharts';
import { 
  TrendingUp, TrendingDown, Users, Target, Clock, AlertCircle, 
  Brain, BarChart3, Calendar, Filter, Download, RefreshCw,
  Zap, Eye, Award, Activity, GitBranch, Layers
} from 'lucide-react';

const COLORS = {
  primary: ['#3B82F6', '#1D4ED8', '#1E40AF', '#1E3A8A'],
  success: ['#10B981', '#059669', '#047857', '#065F46'],
  warning: ['#F59E0B', '#D97706', '#B45309', '#92400E'],
  danger: ['#EF4444', '#DC2626', '#B91C1C', '#991B1B'],
  purple: ['#8B5CF6', '#7C3AED', '#6D28D9', '#5B21B6'],
  gradient: ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe', '#00f2fe']
};

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow-xl border border-gray-200 dark:border-gray-600">
        <p className="font-semibold text-gray-900 dark:text-white mb-2">{label}</p>
        {payload.map((entry, index) => (
          <div key={index} className="flex items-center space-x-2">
            <div 
              className="w-3 h-3 rounded-full" 
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-sm text-gray-600 dark:text-gray-400">{entry.name}:</span>
            <span className="text-sm font-medium text-gray-900 dark:text-white">{entry.value}</span>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

const VelocityChart = ({ data }) => {
  const velocityData = data?.map((item, index) => ({
    week: `Week ${index + 1}`,
    completed: item.completed || Math.floor(Math.random() * 20) + 5,
    planned: item.planned || Math.floor(Math.random() * 25) + 10,
    velocity: item.velocity || Math.floor(Math.random() * 15) + 8
  })) || Array.from({ length: 8 }, (_, i) => ({
    week: `Week ${i + 1}`,
    completed: Math.floor(Math.random() * 20) + 5,
    planned: Math.floor(Math.random() * 25) + 10,
    velocity: Math.floor(Math.random() * 15) + 8
  }));

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
        <Activity className="w-5 h-5 mr-2 text-green-600" />
        Team Velocity Trend
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <ComposedChart data={velocityData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
          <XAxis dataKey="week" tick={{ fontSize: 12 }} stroke="#6B7280" />
          <YAxis tick={{ fontSize: 12 }} stroke="#6B7280" />
          <Tooltip content={<CustomTooltip />} />
          <Legend />
          <Bar dataKey="planned" fill={COLORS.warning[0]} name="Planned" opacity={0.7} />
          <Bar dataKey="completed" fill={COLORS.success[0]} name="Completed" />
          <Line type="monotone" dataKey="velocity" stroke={COLORS.purple[0]} strokeWidth={3} name="Velocity" />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
};

const BurndownChart = ({ data }) => {
  const burndownData = data || Array.from({ length: 14 }, (_, i) => ({
    day: `Day ${i + 1}`,
    ideal: Math.max(0, 100 - (i * 7.14)),
    actual: Math.max(0, 100 - (i * Math.random() * 10)),
    remaining: Math.max(0, 100 - (i * 6.5))
  }));

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
        <TrendingDown className="w-5 h-5 mr-2 text-blue-600" />
        Sprint Burndown
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={burndownData}>
          <defs>
            <linearGradient id="idealGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={COLORS.primary[0]} stopOpacity={0.3}/>
              <stop offset="95%" stopColor={COLORS.primary[0]} stopOpacity={0.1}/>
            </linearGradient>
            <linearGradient id="actualGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={COLORS.danger[0]} stopOpacity={0.3}/>
              <stop offset="95%" stopColor={COLORS.danger[0]} stopOpacity={0.1}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
          <XAxis dataKey="day" tick={{ fontSize: 12 }} stroke="#6B7280" />
          <YAxis tick={{ fontSize: 12 }} stroke="#6B7280" />
          <Tooltip content={<CustomTooltip />} />
          <Legend />
          <Area 
            type="monotone" 
            dataKey="ideal" 
            stroke={COLORS.primary[0]}
            fillOpacity={1} 
            fill="url(#idealGradient)"
            strokeWidth={2}
            name="Ideal Burndown"
          />
          <Area 
            type="monotone" 
            dataKey="actual" 
            stroke={COLORS.danger[0]}
            fillOpacity={1} 
            fill="url(#actualGradient)"
            strokeWidth={2}
            name="Actual Progress"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

const WorkloadHeatmap = ({ data }) => {
  const heatmapData = data || Array.from({ length: 7 }, (_, day) => 
    Array.from({ length: 24 }, (_, hour) => ({
      day: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][day],
      hour,
      value: Math.floor(Math.random() * 10),
      dayIndex: day,
      hourIndex: hour
    }))
  ).flat();

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
        <Layers className="w-5 h-5 mr-2 text-orange-600" />
        Team Activity Heatmap
      </h3>
      <div className="grid grid-cols-24 gap-1">
        {Array.from({ length: 24 }, (_, hour) => (
          <div key={hour} className="text-xs text-center text-gray-500 dark:text-gray-400 mb-1">
            {hour}
          </div>
        ))}
        {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((day, dayIndex) => (
          <React.Fragment key={day}>
            {Array.from({ length: 24 }, (_, hour) => {
              const value = Math.floor(Math.random() * 10);
              const intensity = value / 10;
              return (
                <div
                  key={`${day}-${hour}`}
                  className="aspect-square rounded-sm border border-gray-200 dark:border-gray-600 flex items-center justify-center text-xs"
                  style={{
                    backgroundColor: `rgba(59, 130, 246, ${intensity})`,
                    color: intensity > 0.5 ? 'white' : '#374151'
                  }}
                  title={`${day} ${hour}:00 - ${value} activities`}
                >
                  {value > 0 ? value : ''}
                </div>
              );
            })}
          </React.Fragment>
        ))}
      </div>
      <div className="flex items-center justify-between mt-4 text-xs text-gray-500 dark:text-gray-400">
        <span>Less</span>
        <div className="flex space-x-1">
          {[0.1, 0.3, 0.5, 0.7, 0.9].map((intensity, i) => (
            <div
              key={i}
              className="w-3 h-3 rounded-sm"
              style={{ backgroundColor: `rgba(59, 130, 246, ${intensity})` }}
            />
          ))}
        </div>
        <span>More</span>
      </div>
    </div>
  );
};

const PerformanceRadar = ({ data }) => {
  // Mock radar chart data
  const radarData = [
    { metric: 'Velocity', value: 85, fullMark: 100 },
    { metric: 'Quality', value: 92, fullMark: 100 },
    { metric: 'Collaboration', value: 78, fullMark: 100 },
    { metric: 'Innovation', value: 88, fullMark: 100 },
    { metric: 'Delivery', value: 90, fullMark: 100 },
    { metric: 'Learning', value: 75, fullMark: 100 }
  ];

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
        <Award className="w-5 h-5 mr-2 text-purple-600" />
        Team Performance Radar
      </h3>
      <div className="grid grid-cols-2 gap-4">
        {radarData.map((item, index) => (
          <div key={index} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{item.metric}</span>
            <div className="flex items-center space-x-2">
              <div className="w-20 bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                <div 
                  className="bg-purple-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${item.value}%` }}
                />
              </div>
              <span className="text-sm font-bold text-purple-600 dark:text-purple-400">{item.value}%</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

const IssueTreemap = ({ data }) => {
  const treemapData = Object.entries(data || {}).map(([type, count]) => ({
    name: type,
    size: count,
    fill: COLORS.gradient[Math.floor(Math.random() * COLORS.gradient.length)]
  }));

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
        <GitBranch className="w-5 h-5 mr-2 text-indigo-600" />
        Issue Type Distribution
      </h3>
      <ResponsiveContainer width="100%" height={250}>
        <Treemap
          data={treemapData}
          dataKey="size"
          aspectRatio={4/3}
          stroke="#fff"
          fill="#8884d8"
        />
      </ResponsiveContainer>
    </div>
  );
};

const AdvancedAnalytics = () => {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(false);
  const [dateRange, setDateRange] = useState('30d');
  const [selectedMetric, setSelectedMetric] = useState('velocity');

  useEffect(() => {
    loadAnalytics();
  }, [dateRange]);

  const loadAnalytics = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/jira/team-analytics?date_range=${dateRange}`);
      const data = await response.json();
      if (response.ok) {
        setAnalytics(data);
      }
    } catch (error) {
      console.error('Failed to load analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  const exportData = () => {
    // Export functionality
    console.log('Exporting analytics data...');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600 dark:text-gray-400">Loading advanced analytics...</p>
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
              <div className="p-2 bg-gradient-to-r from-purple-500 to-blue-600 rounded-lg">
                <BarChart3 className="w-8 h-8 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Advanced Analytics</h1>
                <p className="text-sm text-gray-500 dark:text-gray-400">Deep insights and performance metrics</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              {/* Metric Selector */}
              <select 
                value={selectedMetric}
                onChange={(e) => setSelectedMetric(e.target.value)}
                className="px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg text-sm"
              >
                <option value="velocity">Velocity</option>
                <option value="burndown">Burndown</option>
                <option value="workload">Workload</option>
                <option value="performance">Performance</option>
              </select>
              
              {/* Date Range */}
              <select 
                value={dateRange}
                onChange={(e) => setDateRange(e.target.value)}
                className="px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg text-sm"
              >
                <option value="7d">Last 7 days</option>
                <option value="30d">Last 30 days</option>
                <option value="90d">Last 90 days</option>
              </select>
              
              {/* Actions */}
              <button
                onClick={exportData}
                className="flex items-center space-x-2 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
              >
                <Download className="w-4 h-4" />
                <span>Export</span>
              </button>
              
              <button
                onClick={loadAnalytics}
                className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
              >
                <RefreshCw className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="space-y-6">
          
          {/* Key Metrics Row */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="bg-gradient-to-r from-blue-500 to-blue-600 rounded-xl p-6 text-white">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-blue-100 text-sm">Sprint Velocity</p>
                  <p className="text-3xl font-bold">24.5</p>
                  <p className="text-blue-100 text-xs">Story points/sprint</p>
                </div>
                <Activity className="w-8 h-8 text-blue-200" />
              </div>
            </div>
            
            <div className="bg-gradient-to-r from-green-500 to-green-600 rounded-xl p-6 text-white">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-green-100 text-sm">Cycle Time</p>
                  <p className="text-3xl font-bold">3.2</p>
                  <p className="text-green-100 text-xs">Days average</p>
                </div>
                <Clock className="w-8 h-8 text-green-200" />
              </div>
            </div>
            
            <div className="bg-gradient-to-r from-purple-500 to-purple-600 rounded-xl p-6 text-white">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-purple-100 text-sm">Code Quality</p>
                  <p className="text-3xl font-bold">92%</p>
                  <p className="text-purple-100 text-xs">Quality score</p>
                </div>
                <Award className="w-8 h-8 text-purple-200" />
              </div>
            </div>
            
            <div className="bg-gradient-to-r from-orange-500 to-orange-600 rounded-xl p-6 text-white">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-orange-100 text-sm">Team Happiness</p>
                  <p className="text-3xl font-bold">8.7</p>
                  <p className="text-orange-100 text-xs">Out of 10</p>
                </div>
                <Users className="w-8 h-8 text-orange-200" />
              </div>
            </div>
          </div>

          {/* Charts Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <VelocityChart data={analytics?.velocity_data} />
            <BurndownChart data={analytics?.burndown_data} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2">
              <WorkloadHeatmap data={analytics?.workload_data} />
            </div>
            <PerformanceRadar data={analytics?.performance_data} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <IssueTreemap data={analytics?.team_overview?.type_distribution} />
            
            {/* Additional Insights */}
            <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
                <Brain className="w-5 h-5 mr-2 text-indigo-600" />
                AI Recommendations
              </h3>
              <div className="space-y-4">
                <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                  <h4 className="font-medium text-blue-800 dark:text-blue-300 mb-2">Velocity Optimization</h4>
                  <p className="text-sm text-blue-700 dark:text-blue-400">
                    Consider reducing story complexity in upcoming sprints. Current velocity suggests team capacity is at 85%.
                  </p>
                </div>
                
                <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
                  <h4 className="font-medium text-green-800 dark:text-green-300 mb-2">Quality Improvement</h4>
                  <p className="text-sm text-green-700 dark:text-green-400">
                    Code review process is working well. Maintain current practices for sustained quality.
                  </p>
                </div>
                
                <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border border-yellow-200 dark:border-yellow-800">
                  <h4 className="font-medium text-yellow-800 dark:text-yellow-300 mb-2">Workload Balance</h4>
                  <p className="text-sm text-yellow-700 dark:text-yellow-400">
                    Some team members show higher activity during off-hours. Consider workload redistribution.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdvancedAnalytics;