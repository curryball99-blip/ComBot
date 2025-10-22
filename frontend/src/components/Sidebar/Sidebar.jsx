import { AnimatePresence, motion } from 'framer-motion';
import {
  ChevronLeft,
  Clock,
  ExternalLink,
  FileText,
  Menu,
  MessageSquare,
  Plus,
  Settings,
  Upload,
  X
} from 'lucide-react';
import { useEffect, useState } from 'react';
import useChatStore from '../../stores/chatStore';
import useRouteStore from '../../stores/routeStore';
import ComvivaLogo from '../ComvivaLogo';
import ConversationItem from './ConversationItem';

const Sidebar = () => {
  const {
    sidebarOpen,
    conversations,
    currentSessionId,
    isLoadingConversations,
    toggleSidebar,
    toggleUploadModal,
    loadConversations,
    startNewConversation,
    deleteConversation,
    renameConversation,
    setCurrentSession,
  } = useChatStore();

  const { setRoute } = useRouteStore();
  const [collapsed, setCollapsed] = useState(false);



  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  const handleConversationClick = async (sessionId) => {
    if (sessionId !== currentSessionId) {
      await setCurrentSession(sessionId);
    }
  };
  
  const handleConversationClickAndNavigate = async (sessionId) => {
    await handleConversationClick(sessionId);
    setRoute('chat');
  };

  const handleDeleteConversation = async (e, sessionId) => {
    e.stopPropagation();
    if (window.confirm('Are you sure you want to delete this conversation?')) {
      await deleteConversation(sessionId);
    }
  };

  const handleRenameConversation = async (sessionId, newTitle) => {
    await renameConversation(sessionId, newTitle);
  };

  const sidebarVariants = {
    open: {
      x: 0,
      transition: { type: 'spring', stiffness: 300, damping: 30 }
    },
    closed: {
      x: '-100%',
      transition: { type: 'spring', stiffness: 300, damping: 30 }
    }
  };

  return (
    <>
      {/* Mobile backdrop */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={toggleSidebar}
            className="lg:hidden fixed inset-0 bg-gray-900/50 z-40"
          />
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <motion.div
        variants={sidebarVariants}
        animate={sidebarOpen ? 'open' : 'closed'}
        className={`fixed lg:relative top-0 left-0 h-full ${collapsed ? 'w-16' : 'w-80'} bg-white dark:bg-dark-surface border-r border-gray-200 dark:border-dark-border z-50 flex flex-col transition-all duration-300`}
      >
        {/* Header */}
        <div className={`${collapsed ? 'p-2' : 'p-6'} border-b border-gray-200 dark:border-dark-border`}>
          {collapsed ? (
            <div className="flex flex-col items-center space-y-4">
              <button
                onClick={() => setCollapsed(false)}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                title="Expand sidebar"
              >
                <ComvivaLogo variant="orb" className="w-8 h-8" />
              </button>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-3">
                  <ComvivaLogo variant="orb" className="w-8 h-8" />
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900 dark:text-dark-text">Comviva AI</h2>
                    <p className="text-xs text-gray-500 dark:text-dark-muted">A Tech Mahindra Company</p>
                  </div>
                </div>
                <div className="flex items-center space-x-1">
                  <button
                    onClick={() => setCollapsed(true)}
                    className="hidden lg:block p-1 text-gray-500 hover:text-gray-700 dark:text-dark-muted dark:hover:text-dark-text"
                    title="Collapse sidebar"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <button
                    onClick={toggleSidebar}
                    className="lg:hidden p-1 text-gray-500 hover:text-gray-700 dark:text-dark-muted dark:hover:text-dark-text"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>
              </div>

              {/* New Chat Button */}
              <button
                onClick={() => { startNewConversation(); setRoute('chat'); }}
                className="w-full flex items-center justify-center space-x-2 bg-comviva-primary hover:bg-blue-700 text-white py-3 px-4 rounded-lg transition-colors"
              >
                <Plus className="w-4 h-4" />
                <span>New Chat</span>
              </button>
            </>
          )}
        </div>

        {/* Action Buttons */}
        {!collapsed && (
          <div className="p-4 border-b border-gray-200 dark:border-dark-border">
            <div className="grid grid-cols-2 gap-2 mb-2">
              <button
                onClick={toggleUploadModal}
                className="flex items-center justify-center space-x-1 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 py-2 px-2 rounded-lg transition-colors text-xs"
              >
                <Upload className="w-3 h-3" />
                <span>Upload</span>
              </button>
              <button
                onClick={() => setRoute('settings')}
                className="flex items-center justify-center space-x-1 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 py-2 px-2 rounded-lg transition-colors text-xs"
              >
                <Settings className="w-3 h-3" />
                <span>Settings</span>
              </button>
            </div>
            <div className="flex justify-center">
              <button
                onClick={() => setRoute('jira')}
                className="flex items-center justify-center space-x-1 bg-blue-100 hover:bg-blue-200 dark:bg-blue-900 dark:hover:bg-blue-800 text-blue-700 dark:text-blue-300 py-2 px-4 rounded-lg transition-colors text-xs"
              >
                <ExternalLink className="w-3 h-3" />
                <span>JIRA</span>
              </button>
            </div>
          </div>
        )}

        {/* Conversations List */}
        {!collapsed && (
          <div className="flex-1 overflow-hidden">
            <div className="p-4">
              <h3 className="text-sm font-medium text-gray-500 mb-3 flex items-center space-x-2">
                <Clock className="w-4 h-4" />
                <span>Recent Conversations</span>
              </h3>
            </div>
            <div className="flex-1 overflow-y-auto px-4 pb-3 scrollbar-thin" style={{ maxHeight: 'calc(100vh - 350px)' }}>
              {isLoadingConversations ? (
                <div className="space-y-3">
                  {[...Array(5)].map((_, i) => (
                    <div key={i} className="loading-shimmer h-16 rounded-lg"></div>
                  ))}
                </div>
              ) : conversations.length === 0 ? (
                <div className="text-center py-12">
                  <MessageSquare className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                  <p className="text-sm text-gray-500">No conversations yet</p>
                  <p className="text-xs text-gray-400 mt-1">Start a new chat to begin</p>
                </div>
              ) : (
                <div className="space-y-1">
                  {conversations.map((conversation) => (
                    <ConversationItem
                      key={conversation.session_id}
                      conversation={conversation}
                      isActive={currentSessionId === conversation.session_id}
                      onClick={() => handleConversationClickAndNavigate(conversation.session_id)}
                      onDelete={handleDeleteConversation}
                      onRename={handleRenameConversation}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Footer */}
        {!collapsed && (
          <div className="p-4 border-t border-gray-200 dark:border-dark-border">
            <div className="flex items-center justify-between text-xs text-gray-500 dark:text-dark-muted mb-2">
              <div className="flex items-center space-x-1">
                <FileText className="w-3 h-3" />
                <span>{conversations.length} conversations</span>
              </div>
              <div className="text-comviva-primary font-medium">
                v1.0
              </div>
            </div>
            <div className="flex items-center justify-center">
              <ComvivaLogo variant="full" className="h-4 w-auto opacity-70 hover:opacity-100 transition-opacity" />
            </div>
          </div>
        )}
      </motion.div>

      {/* Mobile toggle button */}
      <button
        onClick={toggleSidebar}
        className="lg:hidden fixed top-4 left-4 z-50 p-2 bg-white border border-gray-200 rounded-lg shadow-lg hover:bg-gray-50"
      >
        <Menu className="w-5 h-5" />
      </button>


    </>
  );
};

export default Sidebar;