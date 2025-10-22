import React from 'react';
import { BarChart3, Users, TrendingUp, Search, Brain, Target } from 'lucide-react';

const DashboardNavigation = () => {
  const currentPath = window.location.pathname;
  
  const navigationItems = [
    {
      path: '/jira',
      label: 'Classic JIRA',
      icon: Search,
      description: 'Traditional JIRA interface'
    },
    {
      path: '/jira-enhanced',
      label: 'Enhanced Dashboard',
      icon: BarChart3,
      description: 'Interactive charts and metrics'
    },
    {
      path: '/analytics',
      label: 'Advanced Analytics',
      icon: TrendingUp,
      description: 'Deep insights and AI recommendations'
    }
  ];

  const handleNavigation = (path) => {
    window.location.href = path;
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 shadow-sm border-b dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between py-4">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg">
                <Target className="w-8 h-8 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">JIRA Analytics Suite</h1>
                <p className="text-sm text-gray-500 dark:text-gray-400">Choose your analytics experience</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Cards */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {navigationItems.map((item, index) => {
            const Icon = item.icon;
            const isActive = currentPath === item.path;
            
            return (
              <div
                key={index}
                onClick={() => handleNavigation(item.path)}
                className={`relative group cursor-pointer transform transition-all duration-300 hover:scale-105 ${
                  isActive ? 'ring-2 ring-blue-500' : ''
                }`}
              >
                <div className="bg-white dark:bg-gray-800 rounded-xl p-8 shadow-lg border border-gray-200 dark:border-gray-700 hover:shadow-xl transition-shadow">
                  {/* Icon */}
                  <div className={`inline-flex p-4 rounded-lg mb-4 ${
                    index === 0 ? 'bg-blue-100 dark:bg-blue-900/20' :
                    index === 1 ? 'bg-purple-100 dark:bg-purple-900/20' :
                    'bg-green-100 dark:bg-green-900/20'
                  }`}>
                    <Icon className={`w-8 h-8 ${
                      index === 0 ? 'text-blue-600' :
                      index === 1 ? 'text-purple-600' :
                      'text-green-600'
                    }`} />
                  </div>
                  
                  {/* Content */}
                  <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                    {item.label}
                  </h3>
                  <p className="text-gray-600 dark:text-gray-400 mb-6">
                    {item.description}
                  </p>
                  
                  {/* Features */}
                  <div className="space-y-2">
                    {index === 0 && (
                      <>
                        <div className="flex items-center text-sm text-gray-500 dark:text-gray-400">
                          <div className="w-2 h-2 bg-blue-500 rounded-full mr-2" />
                          Search and filter tickets
                        </div>
                        <div className="flex items-center text-sm text-gray-500 dark:text-gray-400">
                          <div className="w-2 h-2 bg-blue-500 rounded-full mr-2" />
                          Basic analytics and reports
                        </div>
                        <div className="flex items-center text-sm text-gray-500 dark:text-gray-400">
                          <div className="w-2 h-2 bg-blue-500 rounded-full mr-2" />
                          Team performance overview
                        </div>
                      </>
                    )}
                    
                    {index === 1 && (
                      <>
                        <div className="flex items-center text-sm text-gray-500 dark:text-gray-400">
                          <div className="w-2 h-2 bg-purple-500 rounded-full mr-2" />
                          Interactive charts and graphs
                        </div>
                        <div className="flex items-center text-sm text-gray-500 dark:text-gray-400">
                          <div className="w-2 h-2 bg-purple-500 rounded-full mr-2" />
                          Clickable metrics cards
                        </div>
                        <div className="flex items-center text-sm text-gray-500 dark:text-gray-400">
                          <div className="w-2 h-2 bg-purple-500 rounded-full mr-2" />
                          Real-time data visualization
                        </div>
                      </>
                    )}
                    
                    {index === 2 && (
                      <>
                        <div className="flex items-center text-sm text-gray-500 dark:text-gray-400">
                          <div className="w-2 h-2 bg-green-500 rounded-full mr-2" />
                          Advanced velocity tracking
                        </div>
                        <div className="flex items-center text-sm text-gray-500 dark:text-gray-400">
                          <div className="w-2 h-2 bg-green-500 rounded-full mr-2" />
                          AI-powered insights
                        </div>
                        <div className="flex items-center text-sm text-gray-500 dark:text-gray-400">
                          <div className="w-2 h-2 bg-green-500 rounded-full mr-2" />
                          Predictive analytics
                        </div>
                      </>
                    )}
                  </div>
                  
                  {/* Action Button */}
                  <div className="mt-6">
                    <button className={`w-full py-3 px-4 rounded-lg font-medium transition-colors ${
                      index === 0 ? 'bg-blue-600 hover:bg-blue-700 text-white' :
                      index === 1 ? 'bg-purple-600 hover:bg-purple-700 text-white' :
                      'bg-green-600 hover:bg-green-700 text-white'
                    }`}>
                      {isActive ? 'Currently Active' : 'Open Dashboard'}
                    </button>
                  </div>
                  
                  {/* Active Indicator */}
                  {isActive && (
                    <div className="absolute top-4 right-4">
                      <div className="w-3 h-3 bg-blue-500 rounded-full animate-pulse" />
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
        
        {/* Quick Stats */}
        <div className="mt-12 bg-white dark:bg-gray-800 rounded-xl p-8 shadow-lg border border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-6 flex items-center">
            <Brain className="w-5 h-5 mr-2 text-indigo-600" />
            Quick Overview
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="text-center">
              <div className="text-3xl font-bold text-blue-600 dark:text-blue-400 mb-2">3</div>
              <div className="text-sm text-gray-600 dark:text-gray-400">Dashboard Views</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-green-600 dark:text-green-400 mb-2">15+</div>
              <div className="text-sm text-gray-600 dark:text-gray-400">Chart Types</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-purple-600 dark:text-purple-400 mb-2">AI</div>
              <div className="text-sm text-gray-600 dark:text-gray-400">Powered Insights</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-orange-600 dark:text-orange-400 mb-2">Real-time</div>
              <div className="text-sm text-gray-600 dark:text-gray-400">Data Updates</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardNavigation;