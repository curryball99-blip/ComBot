// Demo data generator for showcasing charts and visualizations

export const generateDashboardData = () => ({
  summary: {
    total_tickets: 1247,
    active_tickets: 342,
    active_percentage: 27.4,
    resolved_tickets: 905,
    resolved_percentage: 72.6,
    recent_updates: 45
  },
  status_distribution: {
    'To Do': 156,
    'In Progress': 89,
    'Code Review': 34,
    'Testing': 28,
    'Done': 567,
    'Closed': 338,
    'Blocked': 12,
    'On Hold': 23
  },
  priority_distribution: {
    'Critical': 23,
    'High': 145,
    'Medium': 678,
    'Low': 234,
    'Trivial': 167
  },
  type_distribution: {
    'Bug': 345,
    'Story': 456,
    'Task': 234,
    'Epic': 67,
    'Sub-task': 145
  },
  assignee_distribution: {
    'John Smith': 89,
    'Sarah Johnson': 76,
    'Mike Chen': 65,
    'Emily Davis': 58,
    'Alex Rodriguez': 52,
    'Lisa Wang': 48,
    'David Brown': 43,
    'Anna Wilson': 39
  },
  recent_tickets: Array.from({ length: 20 }, (_, i) => ({
    key: `PROJ-${1000 + i}`,
    summary: `Sample ticket ${i + 1} - ${['Bug fix', 'Feature implementation', 'Code refactoring', 'Testing'][i % 4]}`,
    status: ['To Do', 'In Progress', 'Done', 'Testing'][i % 4],
    assignee: ['John Smith', 'Sarah Johnson', 'Mike Chen', 'Emily Davis'][i % 4],
    priority: ['High', 'Medium', 'Low'][i % 3],
    url: `https://jira.example.com/browse/PROJ-${1000 + i}`
  }))
});

export const generateTeamAnalytics = () => ({
  summary_cards: [
    {
      title: 'Team Members',
      value: '8',
      subtitle: 'Active contributors',
      color: 'blue'
    },
    {
      title: 'Total Tickets',
      value: '1,247',
      subtitle: 'This period',
      color: 'green'
    },
    {
      title: 'Avg Completion',
      value: '72.6%',
      subtitle: 'Success rate',
      color: 'purple'
    },
    {
      title: 'Avg Resolution',
      value: '3.2 days',
      subtitle: 'Time to resolve',
      color: 'orange'
    }
  ],
  individual_performance: [
    {
      assignee: 'John Smith',
      productivity_score: 92,
      completion_rate: 89,
      performance_trend: 'improving',
      metrics: { done: 45, in_progress: 8, todo: 12 }
    },
    {
      assignee: 'Sarah Johnson',
      productivity_score: 88,
      completion_rate: 85,
      performance_trend: 'stable',
      metrics: { done: 38, in_progress: 6, todo: 9 }
    },
    {
      assignee: 'Mike Chen',
      productivity_score: 85,
      completion_rate: 82,
      performance_trend: 'improving',
      metrics: { done: 34, in_progress: 7, todo: 11 }
    },
    {
      assignee: 'Emily Davis',
      productivity_score: 79,
      completion_rate: 76,
      performance_trend: 'declining',
      metrics: { done: 29, in_progress: 9, todo: 15 }
    },
    {
      assignee: 'Alex Rodriguez',
      productivity_score: 83,
      completion_rate: 80,
      performance_trend: 'stable',
      metrics: { done: 31, in_progress: 5, todo: 8 }
    },
    {
      assignee: 'Lisa Wang',
      productivity_score: 90,
      completion_rate: 87,
      performance_trend: 'improving',
      metrics: { done: 42, in_progress: 4, todo: 6 }
    }
  ],
  productivity_insights: [
    {
      assignee: 'John Smith',
      insights: [
        { type: 'positive', message: 'Consistently high completion rate with quality deliverables' },
        { type: 'info', message: 'Leading team in story point completion this sprint' }
      ]
    },
    {
      assignee: 'Sarah Johnson',
      insights: [
        { type: 'positive', message: 'Excellent code review participation and mentoring' },
        { type: 'info', message: 'Balanced workload with steady progress' }
      ]
    },
    {
      assignee: 'Mike Chen',
      insights: [
        { type: 'positive', message: 'Showing improvement in velocity over last 3 sprints' },
        { type: 'warning', message: 'Consider reducing complexity of assigned tasks' }
      ]
    },
    {
      assignee: 'Emily Davis',
      insights: [
        { type: 'concern', message: 'Completion rate has decreased in recent sprints' },
        { type: 'warning', message: 'May need additional support or workload adjustment' }
      ]
    }
  ],
  team_overview: {
    status_distribution: {
      'To Do': 156,
      'In Progress': 89,
      'Code Review': 34,
      'Testing': 28,
      'Done': 567,
      'Closed': 338
    },
    priority_distribution: {
      'Critical': 23,
      'High': 145,
      'Medium': 678,
      'Low': 234
    },
    type_distribution: {
      'Bug': 345,
      'Story': 456,
      'Task': 234,
      'Epic': 67
    }
  }
});

export const generateVelocityData = () => 
  Array.from({ length: 8 }, (_, i) => ({
    week: `Week ${i + 1}`,
    completed: Math.floor(Math.random() * 20) + 15,
    planned: Math.floor(Math.random() * 25) + 20,
    velocity: Math.floor(Math.random() * 15) + 12
  }));

export const generateBurndownData = () =>
  Array.from({ length: 14 }, (_, i) => ({
    day: `Day ${i + 1}`,
    ideal: Math.max(0, 100 - (i * 7.14)),
    actual: Math.max(0, 100 - (i * (5 + Math.random() * 4))),
    remaining: Math.max(0, 100 - (i * 6.5))
  }));

export const generateIndividualAnalysis = (assignee) => ({
  performance_summary: {
    completion_rate: Math.floor(Math.random() * 20) + 75,
    avg_resolution_days: (Math.random() * 3 + 2).toFixed(1),
    status_breakdown: {
      'Done': Math.floor(Math.random() * 30) + 20,
      'In Progress': Math.floor(Math.random() * 10) + 3,
      'To Do': Math.floor(Math.random() * 15) + 5,
      'Testing': Math.floor(Math.random() * 8) + 2
    },
    productivity_insights: [
      'Strong performance in current sprint with consistent delivery',
      'Good collaboration with team members and stakeholders',
      'Maintains high code quality standards'
    ]
  },
  status_timeline: Array.from({ length: 25 }, (_, i) => ({
    key: `PROJ-${2000 + i}`,
    summary: `Task ${i + 1} - ${['Implementation', 'Bug fix', 'Testing', 'Review'][i % 4]}`,
    status: ['Done', 'In Progress', 'Testing', 'Code Review'][i % 4],
    priority: ['High', 'Medium', 'Low'][i % 3],
    updated: new Date(Date.now() - i * 24 * 60 * 60 * 1000).toISOString(),
    url: `https://jira.example.com/browse/PROJ-${2000 + i}`
  }))
});