import { useEffect } from 'react';
import { Toaster } from 'react-hot-toast';
import ChatInterface from './components/Chat/ChatInterface';
import JiraPageWithSidebar from './components/JiraPageWithSidebar';
import SettingsPage from './components/SettingsPage';
import Sidebar from './components/Sidebar/Sidebar';
import UploadModal from './components/Upload/UploadModal';

import { systemAPI } from './services/api';
import useChatStore from './stores/chatStore';
import useRouteStore from './stores/routeStore';
import useThemeStore from './stores/themeStore';

function App() {
  const { sidebarOpen, initialize } = useChatStore();
  const { initializeTheme } = useThemeStore();
  const { currentRoute } = useRouteStore();

  useEffect(() => {
    // Initialize theme
    initializeTheme();

    // Check backend status on app start
    const checkBackend = async () => {
      try {
        const status = await systemAPI.checkBackendStatus();
        if (!status.available) {
          console.warn('Backend is not available:', status.error);
        }
      } catch (error) {
        console.error('Failed to check backend status:', error);
      }
    };

    checkBackend();
    // Initialize chat store (loads conversations and creates first session if needed)
    initialize();
  }, [initialize, initializeTheme]);

  // Route-based rendering
  if (currentRoute === 'jira') {
    return (
      <div className="h-screen flex bg-gray-50 overflow-hidden">
        <Sidebar />
        <div className="flex-1 overflow-y-auto">
          <JiraPageWithSidebar />
        </div>
        <Toaster position="top-right" />
      </div>
    );
  }

  if (currentRoute === 'settings') {
    return (
      <div className="h-screen flex bg-gray-50 dark:bg-dark-bg overflow-hidden">
        <Sidebar />
        <SettingsPage />
        <Toaster position="top-right" />
      </div>
    );
  }



  return (
    <div className="h-screen flex bg-gray-50 dark:bg-dark-bg">
      {/* Sidebar */}
      <Sidebar />

      {/* Main Chat Area */}
      <div className={`
        flex-1 flex flex-col transition-all duration-300
        ${sidebarOpen ? 'lg:ml-0' : 'ml-0'}
      `}>
        <ChatInterface />
      </div>

      {/* Modals */}
      <UploadModal />

      {/* Toast Notifications */}
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          className: 'text-sm',
          style: {
            background: '#fff',
            border: '1px solid #e5e7eb',
            borderRadius: '0.75rem',
            boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
          },
          success: {
            iconTheme: {
              primary: '#10b981',
              secondary: '#fff',
            },
          },
          error: {
            iconTheme: {
              primary: '#ef4444',
              secondary: '#fff',
            },
          },
        }}
      />
    </div>
  );
}

export default App;