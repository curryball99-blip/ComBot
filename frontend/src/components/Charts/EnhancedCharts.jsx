import React, { useState } from 'react';
import { 
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, 
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  AreaChart, Area, RadialBarChart, RadialBar, ComposedChart
} from 'recharts';
import { TrendingUp, TrendingDown, Users, Target, Clock, AlertCircle } from 'lucide-react';

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
      <div className="bg-white dark:bg-gray-800 p-3 rounded-lg shadow-lg border border-gray-200 dark:border-gray-600">
        <p className="font-medium text-gray-900 dark:text-white">{label}</p>
        {payload.map((entry, index) => (
          <p key={index} className="text-sm" style={{ color: entry.color }}>
            {entry.name}: {entry.value}
          </p>
        ))}
      </div>
    );
  }
  return null;
};

export const StatusDistributionChart = ({ data, onSegmentClick }) => {
  const chartData = Object.entries(data || {}).map(([status, count]) => ({
    name: status,
    value: count,
    percentage: ((count / Object.values(data).reduce((a, b) => a + b, 0)) * 100).toFixed(1)
  }));

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
        <Target className="w-5 h-5 mr-2 text-blue-600" />
        Status Distribution
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            outerRadius={100}
            innerRadius={40}
            paddingAngle={2}
            dataKey="value"
            onClick={onSegmentClick}
            className="cursor-pointer"
          >
            {chartData.map((entry, index) => (
              <Cell 
                key={`cell-${index}`} 
                fill={COLORS.primary[index % COLORS.primary.length]}
                stroke="#fff"
                strokeWidth={2}
              />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          <Legend 
            verticalAlign="bottom" 
            height={36}
            formatter={(value, entry) => `${value} (${entry.payload.percentage}%)`}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
};

export const TeamPerformanceChart = ({ data, onBarClick }) => {
  const chartData = data?.map(member => ({
    name: member.assignee.split(' ')[0], // First name only
    completed: member.metrics.done,
    inProgress: member.metrics.in_progress,
    todo: member.metrics.todo,
    score: member.productivity_score
  })) || [];

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
        <Users className="w-5 h-5 mr-2 text-purple-600" />
        Team Performance Overview
      </h3>
      <ResponsiveContainer width="100%" height={350}>
        <ComposedChart data={chartData} onClick={onBarClick}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
          <XAxis 
            dataKey="name" 
            tick={{ fontSize: 12 }}
            stroke="#6B7280"
          />
          <YAxis 
            yAxisId="left"
            tick={{ fontSize: 12 }}
            stroke="#6B7280"
          />
          <YAxis 
            yAxisId="right" 
            orientation="right"
            tick={{ fontSize: 12 }}
            stroke="#6B7280"
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend />
          <Bar yAxisId="left" dataKey="completed" stackId="a" fill={COLORS.success[0]} name="Completed" />
          <Bar yAxisId="left" dataKey="inProgress" stackId="a" fill={COLORS.warning[0]} name="In Progress" />
          <Bar yAxisId="left" dataKey="todo" stackId="a" fill={COLORS.danger[0]} name="To Do" />
          <Line yAxisId="right" type="monotone" dataKey="score" stroke={COLORS.purple[0]} strokeWidth={3} name="Score" />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
};

export const TrendChart = ({ data, title, color = "blue" }) => {
  const trendData = data?.map((item, index) => ({
    ...item,
    trend: index > 0 ? (item.value > data[index - 1].value ? 'up' : 'down') : 'neutral'
  })) || [];

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
        <TrendingUp className="w-5 h-5 mr-2 text-green-600" />
        {title}
      </h3>
      <ResponsiveContainer width="100%" height={250}>
        <AreaChart data={trendData}>
          <defs>
            <linearGradient id={`gradient-${color}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={COLORS[color]?.[0] || COLORS.primary[0]} stopOpacity={0.8}/>
              <stop offset="95%" stopColor={COLORS[color]?.[0] || COLORS.primary[0]} stopOpacity={0.1}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
          <XAxis dataKey="name" tick={{ fontSize: 12 }} stroke="#6B7280" />
          <YAxis tick={{ fontSize: 12 }} stroke="#6B7280" />
          <Tooltip content={<CustomTooltip />} />
          <Area 
            type="monotone" 
            dataKey="value" 
            stroke={COLORS[color]?.[0] || COLORS.primary[0]}
            fillOpacity={1} 
            fill={`url(#gradient-${color})`}
            strokeWidth={3}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

export const PriorityRadialChart = ({ data }) => {
  const chartData = Object.entries(data || {}).map(([priority, count], index) => ({
    name: priority,
    value: count,
    fill: COLORS.gradient[index % COLORS.gradient.length]
  }));

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
        <AlertCircle className="w-5 h-5 mr-2 text-orange-600" />
        Priority Distribution
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <RadialBarChart cx="50%" cy="50%" innerRadius="20%" outerRadius="90%" data={chartData}>
          <RadialBar
            minAngle={15}
            label={{ position: 'insideStart', fill: '#fff', fontSize: 12 }}
            background
            clockWise
            dataKey="value"
          />
          <Legend 
            iconSize={10} 
            layout="vertical" 
            verticalAlign="middle" 
            align="right"
          />
          <Tooltip content={<CustomTooltip />} />
        </RadialBarChart>
      </ResponsiveContainer>
    </div>
  );
};

export const MetricCard = ({ title, value, subtitle, icon: Icon, color = "blue", trend, onClick, clickable = false }) => {
  const colorClasses = {
    blue: "border-blue-500 text-blue-600 bg-blue-50 dark:bg-blue-900/20",
    green: "border-green-500 text-green-600 bg-green-50 dark:bg-green-900/20",
    purple: "border-purple-500 text-purple-600 bg-purple-50 dark:bg-purple-900/20",
    orange: "border-orange-500 text-orange-600 bg-orange-50 dark:bg-orange-900/20",
    red: "border-red-500 text-red-600 bg-red-50 dark:bg-red-900/20"
  };

  return (
    <div 
      className={`bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border-l-4 ${colorClasses[color]} 
        ${clickable ? 'cursor-pointer hover:shadow-md transform hover:scale-105 transition-all duration-200' : ''}`}
      onClick={clickable ? onClick : undefined}
    >
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">{title}</p>
          <div className="flex items-center space-x-2">
            <p className={`text-3xl font-bold ${colorClasses[color].split(' ')[1]} dark:${colorClasses[color].split(' ')[1]}`}>
              {value}
            </p>
            {trend && (
              <div className="flex items-center">
                {trend > 0 ? (
                  <TrendingUp className="w-4 h-4 text-green-500" />
                ) : (
                  <TrendingDown className="w-4 h-4 text-red-500" />
                )}
                <span className={`text-xs ml-1 ${trend > 0 ? 'text-green-500' : 'text-red-500'}`}>
                  {Math.abs(trend)}%
                </span>
              </div>
            )}
          </div>
          {subtitle && (
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{subtitle}</p>
          )}
        </div>
        <div className={`p-3 rounded-full ${colorClasses[color]}`}>
          <Icon className={`w-6 h-6 ${colorClasses[color].split(' ')[1]}`} />
        </div>
      </div>
    </div>
  );
};

export const InteractiveList = ({ title, items, onItemClick, icon: Icon, color = "blue" }) => {
  const [hoveredItem, setHoveredItem] = useState(null);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
        <Icon className={`w-5 h-5 mr-2 text-${color}-600`} />
        {title}
      </h3>
      <div className="space-y-2 max-h-64 overflow-y-auto">
        {items?.map((item, index) => (
          <div
            key={index}
            className={`p-3 rounded-lg cursor-pointer transition-all duration-200 ${
              hoveredItem === index 
                ? 'bg-blue-50 dark:bg-blue-900/20 transform scale-105' 
                : 'bg-gray-50 dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600'
            }`}
            onClick={() => onItemClick?.(item)}
            onMouseEnter={() => setHoveredItem(index)}
            onMouseLeave={() => setHoveredItem(null)}
          >
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium text-gray-900 dark:text-white truncate">
                {item.name || item.key || item.assignee}
              </span>
              <span className={`text-sm font-bold text-${color}-600 dark:text-${color}-400`}>
                {item.value || item.count}
              </span>
            </div>
            {item.subtitle && (
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 truncate">
                {item.subtitle}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};