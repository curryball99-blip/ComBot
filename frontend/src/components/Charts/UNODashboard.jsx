import React from 'react';
import ChartRenderer from './ChartRenderer';
import { TrendingUp, Shield, MessageSquare, DollarSign } from 'lucide-react';

const UNODashboard = ({ dashboardType = 'overview' }) => {
  // Sample UNO data
  const messagingData = [
    { name: 'SMS', value: 45000, color: '#0088FE' },
    { name: 'MMS', value: 12000, color: '#00C49F' },
    { name: 'RCS', value: 8000, color: '#FFBB28' },
    { name: 'OTT', value: 15000, color: '#FF8042' }
  ];

  const securityData = [
    { name: 'Jan', threats: 120, blocked: 118 },
    { name: 'Feb', threats: 98, blocked: 96 },
    { name: 'Mar', threats: 156, blocked: 154 },
    { name: 'Apr', threats: 89, blocked: 87 },
    { name: 'May', threats: 134, blocked: 132 }
  ];

  const revenueData = [
    { name: 'Q1', revenue: 2.4, saved: 0.8 },
    { name: 'Q2', revenue: 2.8, saved: 1.2 },
    { name: 'Q3', revenue: 3.1, saved: 1.5 },
    { name: 'Q4', revenue: 3.6, saved: 1.8 }
  ];

  const KPICard = ({ title, value, icon: Icon, trend, color }) => (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-600">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-600 dark:text-gray-400">{title}</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{value}</p>
          {trend && (
            <p className={`text-sm ${trend > 0 ? 'text-green-600' : 'text-red-600'}`}>
              {trend > 0 ? '+' : ''}{trend}%
            </p>
          )}
        </div>
        <Icon className={`w-8 h-8 ${color}`} />
      </div>
    </div>
  );

  if (dashboardType === 'messaging') {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KPICard title="Total Messages" value="80K" icon={MessageSquare} trend={12} color="text-blue-500" />
          <KPICard title="Success Rate" value="99.2%" icon={TrendingUp} trend={0.3} color="text-green-500" />
        </div>
        <ChartRenderer 
          type="pie" 
          data={messagingData} 
          title="UNO Messaging Distribution"
          config={{ valueKey: 'value' }}
        />
      </div>
    );
  }

  if (dashboardType === 'security') {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KPICard title="Threats Blocked" value="597" icon={Shield} trend={-8} color="text-red-500" />
          <KPICard title="Block Rate" value="99.1%" icon={TrendingUp} trend={0.2} color="text-green-500" />
        </div>
        <ChartRenderer 
          type="bar" 
          data={securityData} 
          title="UNO Firewall - Threat Detection & Blocking"
          config={{ xKey: 'name', yKey: 'threats' }}
        />
      </div>
    );
  }

  // Default overview dashboard
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPICard title="Messages/Day" value="80K" icon={MessageSquare} trend={12} color="text-blue-500" />
        <KPICard title="Security Score" value="99.1%" icon={Shield} trend={0.2} color="text-green-500" />
        <KPICard title="Revenue Protected" value="$1.8M" icon={DollarSign} trend={15} color="text-yellow-500" />
        <KPICard title="Uptime" value="99.9%" icon={TrendingUp} trend={0.1} color="text-purple-500" />
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ChartRenderer 
          type="line" 
          data={revenueData} 
          title="Revenue Protection Trends"
          config={{ xKey: 'name', yKey: 'saved' }}
        />
        <ChartRenderer 
          type="pie" 
          data={messagingData} 
          title="Message Type Distribution"
          config={{ valueKey: 'value' }}
        />
      </div>
    </div>
  );
};

export default UNODashboard;