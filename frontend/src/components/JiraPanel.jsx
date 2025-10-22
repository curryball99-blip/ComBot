import React, { useState, useEffect } from 'react';
import { Search, Plus, ExternalLink, MessageSquare, BarChart3, TrendingUp } from 'lucide-react';

const JiraPanel = ({ isOpen, onClose }) => {
  const [tickets, setTickets] = useState([]);
  const [projects, setProjects] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [activeTab, setActiveTab] = useState('search');
  const [dashboardData, setDashboardData] = useState(null);
  const [newTicket, setNewTicket] = useState({
    project_key: '',
    summary: '',
    description: '',
    issue_type: 'Task'
  });

  useEffect(() => {
    if (isOpen) {
      loadProjects();
      if (activeTab === 'dashboard') {
        loadDashboard();
      }
    }
  }, [isOpen, activeTab]);

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
      const response = await fetch('/api/jira/dashboard');
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
      const response = await fetch(`/api/jira/search?query=${encodeURIComponent(searchQuery)}&max_results=10`);
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

  const createTicket = async () => {
    if (!newTicket.project_key || !newTicket.summary) return;
    
    setLoading(true);
    try {
      const response = await fetch('/api/jira/ticket', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newTicket)
      });
      
      if (response.ok) {
        const result = await response.json();
        alert(`Ticket created: ${result.key}`);
        setShowCreateForm(false);
        setNewTicket({ project_key: '', summary: '', description: '', issue_type: 'Task' });
      }
    } catch (error) {
      console.error('Create failed:', error);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg w-full max-w-4xl h-5/6 flex flex-col">
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-xl font-semibold">JIRA Integration</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">×</button>
        </div>
        
        {/* Tabs */}
        <div className="flex border-b">
          <button
            onClick={() => setActiveTab('search')}
            className={`px-4 py-2 ${activeTab === 'search' ? 'border-b-2 border-blue-500 text-blue-600' : 'text-gray-500'}`}
          >
            <Search size={16} className="inline mr-1" /> Search
          </button>
          <button
            onClick={() => setActiveTab('dashboard')}
            className={`px-4 py-2 ${activeTab === 'dashboard' ? 'border-b-2 border-blue-500 text-blue-600' : 'text-gray-500'}`}
          >
            <BarChart3 size={16} className="inline mr-1" /> Dashboard
          </button>
        </div>
        
        <div className="flex-1 flex">
          {activeTab === 'search' && (
            <>
              {/* Search Panel */}
              <div className="w-1/2 p-4 border-r">
            <div className="flex gap-2 mb-4">
              <input
                type="text"
                placeholder="Search tickets..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && searchTickets()}
                className="flex-1 px-3 py-2 border rounded-lg"
              />
              <button
                onClick={searchTickets}
                disabled={loading}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                <Search size={16} />
              </button>
            </div>
            
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {tickets.map((ticket) => (
                <div key={ticket.key} className="p-3 border rounded-lg hover:bg-gray-50">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-blue-600">{ticket.key}</span>
                    <a
                      href={ticket.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-gray-500 hover:text-gray-700"
                    >
                      <ExternalLink size={14} />
                    </a>
                  </div>
                  <p className="text-sm text-gray-800 mt-1">{ticket.summary}</p>
                  <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
                    <span className="px-2 py-1 bg-gray-100 rounded">{ticket.status}</span>
                    <span>{ticket.assignee}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
          
              {/* Create Panel */}
              <div className="w-1/2 p-4">
            <button
              onClick={() => setShowCreateForm(!showCreateForm)}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 mb-4"
            >
              <Plus size={16} />
              Create Ticket
            </button>
            
            {showCreateForm && (
              <div className="space-y-4">
                <select
                  value={newTicket.project_key}
                  onChange={(e) => setNewTicket({...newTicket, project_key: e.target.value})}
                  className="w-full px-3 py-2 border rounded-lg"
                >
                  <option value="">Select Project</option>
                  {projects.map((project) => (
                    <option key={project.key} value={project.key}>
                      {project.name} ({project.key})
                    </option>
                  ))}
                </select>
                
                <input
                  type="text"
                  placeholder="Summary"
                  value={newTicket.summary}
                  onChange={(e) => setNewTicket({...newTicket, summary: e.target.value})}
                  className="w-full px-3 py-2 border rounded-lg"
                />
                
                <textarea
                  placeholder="Description"
                  value={newTicket.description}
                  onChange={(e) => setNewTicket({...newTicket, description: e.target.value})}
                  rows={4}
                  className="w-full px-3 py-2 border rounded-lg"
                />
                
                <select
                  value={newTicket.issue_type}
                  onChange={(e) => setNewTicket({...newTicket, issue_type: e.target.value})}
                  className="w-full px-3 py-2 border rounded-lg"
                >
                  <option value="Task">Task</option>
                  <option value="Bug">Bug</option>
                  <option value="Story">Story</option>
                </select>
                
                <button
                  onClick={createTicket}
                  disabled={loading || !newTicket.project_key || !newTicket.summary}
                  className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {loading ? 'Creating...' : 'Create Ticket'}
                </button>
              </div>
            )}
          </div>
            </>
          )}
          
          {activeTab === 'dashboard' && (
            <div className="w-full p-4 overflow-y-auto" style={{maxHeight: 'calc(100vh - 200px)'}}>
              {loading ? (
                <div className="text-center py-8">Loading dashboard...</div>
              ) : dashboardData?.error ? (
                <div className="text-red-500 text-center py-8">{dashboardData.error}</div>
              ) : dashboardData ? (
                <div className="space-y-6">
                  {/* Summary Cards */}
                  <div className="grid grid-cols-3 gap-4">
                    <div className="bg-blue-50 p-4 rounded-lg">
                      <div className="text-2xl font-bold text-blue-600">{dashboardData.summary?.mbsl3_open || 0}</div>
                      <div className="text-sm text-gray-600">MBSL3 Open</div>
                    </div>
                    <div className="bg-green-50 p-4 rounded-lg">
                      <div className="text-2xl font-bold text-green-600">{dashboardData.summary?.uno_open || 0}</div>
                      <div className="text-sm text-gray-600">UNO Open</div>
                    </div>
                    <div className="bg-orange-50 p-4 rounded-lg">
                      <div className="text-2xl font-bold text-orange-600">{dashboardData.summary?.recent_updates || 0}</div>
                      <div className="text-sm text-gray-600">Recent Updates</div>
                    </div>
                  </div>
                  
                  {/* Status Breakdown */}
                  {dashboardData.mbsl3_status && Object.keys(dashboardData.mbsl3_status).length > 0 && (
                    <div>
                      <h3 className="text-lg font-semibold mb-3">MBSL3 Status Breakdown</h3>
                      <div className="grid grid-cols-2 gap-2">
                        {Object.entries(dashboardData.mbsl3_status).map(([status, count]) => (
                          <div key={status} className="flex justify-between p-2 bg-gray-50 rounded">
                            <span className="text-sm">{status}</span>
                            <span className="text-sm font-medium">{count}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Recent Tickets */}
                  {dashboardData.recent_tickets && dashboardData.recent_tickets.length > 0 && (
                    <div>
                      <h3 className="text-lg font-semibold mb-3">Recent Activity (MBSL3 & UNO)</h3>
                      <div className="space-y-2 max-h-64 overflow-y-auto">
                        {dashboardData.recent_tickets.map((ticket) => (
                          <div key={ticket.key} className="p-3 border rounded-lg hover:bg-gray-50">
                            <div className="flex items-center justify-between">
                              <span className="font-medium text-blue-600">{ticket.key}</span>
                              <a href={ticket.url} target="_blank" rel="noopener noreferrer" className="text-gray-500 hover:text-gray-700">
                                <ExternalLink size={14} />
                              </a>
                            </div>
                            <p className="text-sm text-gray-800 mt-1">{ticket.summary}</p>
                            <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
                              <span className="px-2 py-1 bg-gray-100 rounded">{ticket.status}</span>
                              <span>{ticket.assignee}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-8">No dashboard data available</div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default JiraPanel;