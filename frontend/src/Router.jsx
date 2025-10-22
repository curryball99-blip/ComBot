import React from 'react';
import JiraPage from './components/JiraPage';
import EnhancedJiraDashboard from './components/EnhancedJiraDashboard';
import AdvancedAnalytics from './components/AdvancedAnalytics';
import DashboardNavigation from './components/DashboardNavigation';

const Router = () => {
  const path = window.location.pathname;
  
  if (path === '/jira') {
    return <JiraPage />;
  }
  
  if (path === '/jira-enhanced') {
    return <EnhancedJiraDashboard />;
  }
  
  if (path === '/analytics') {
    return <AdvancedAnalytics />;
  }
  
  if (path === '/dashboards') {
    return <DashboardNavigation />;
  }
  
  // Default to main app
  return null;
};

export default Router;