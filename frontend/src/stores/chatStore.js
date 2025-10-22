import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { chatAPI, sessionAPI } from '../services/api';

const useChatStore = create(
  persist(
    (set, get) => ({
      // Current conversation state
      currentSessionId: null,
      messages: [],
      isLoading: false,
      isTyping: false,
      error: null,

      // Conversation management
      conversations: [],
      isLoadingConversations: false,

      // UI state
      sidebarOpen: true,
      uploadModalOpen: false,

      // Initialize store (load conversations on app start)
      initialize: async () => {
        console.log('🚀 Initializing chat store...');
        try {
          await get().loadConversations();

          // If no current session and no conversations, create first one
          const { currentSessionId, conversations } = get();
          if (!currentSessionId && conversations.length === 0) {
            await get().startNewConversation('Welcome Chat');
          }

          console.log('✅ Chat store initialized');
        } catch (error) {
          console.error('❌ Failed to initialize chat store:', error);
        }
      },

      // Actions
      setCurrentSession: async (sessionId) => {
        const { currentSessionId } = get();

        // Don't reload if it's the same session
        if (currentSessionId === sessionId) {
          return;
        }

        console.log('🔄 Switching to session:', sessionId);

        // Load conversation history if sessionId exists
        if (sessionId) {
          set({ currentSessionId: sessionId, error: null });
          await get().loadConversationHistory(sessionId);
        } else {
          // Only clear messages for new conversation
          set({ currentSessionId: sessionId, messages: [], error: null });
        }
      },

      // Send a message (temporarily forcing non-streaming until backend streaming stabilized)
      sendMessage: async (messageText, streaming = false, useInternetSearch = false, aiParams = {}) => {
        const { currentSessionId } = get();

        set({ isLoading: true, error: null });

        // Add user message immediately to UI
        const userMessage = {
          id: Date.now().toString(),
          type: 'user',
          content: messageText,
          timestamp: new Date().toISOString(),
        };

        set((state) => ({
          messages: [...state.messages, userMessage],
          isTyping: true,
        }));

        try {
          {
            // Non-streaming response (fallback)
            // Ensure UI defaults (can be overridden by caller-supplied aiParams)
            const mergedParams = { legacy_mode: true, ...aiParams };
            const response = await chatAPI.sendMessage(messageText, currentSessionId, false, useInternetSearch, mergedParams);

            const botMessage = {
              id: (Date.now() + 1).toString(),
              type: 'bot',
              content: response.response,
              timestamp: response.timestamp || new Date().toISOString(),
              sources: response.sources || [],
              session_id: response.session_id,
            };

            set((state) => ({
              messages: [...state.messages, botMessage],
              currentSessionId: response.session_id,
              isLoading: false,
              isTyping: false,
            }));

            get().loadConversations();
          }

        } catch (error) {
          console.error('Failed to send message:', error);

          // Add error message
          const errorMessage = {
            id: (Date.now() + 1).toString(),
            type: 'error',
            content: error.message || 'Failed to get response. Please try again.',
            timestamp: new Date().toISOString(),
          };

          set((state) => ({
            messages: [...state.messages, errorMessage],
            isLoading: false,
            isTyping: false,
            error: error.message,
          }));
        }
      },

      // Load conversation history (UPDATED for new API)
      loadConversationHistory: async (sessionId) => {
        if (!sessionId) return;

        set({ isLoading: true, error: null });

        try {
          console.log('📜 Loading history for session:', sessionId);

          // Use new session API
          const history = await sessionAPI.getSessionHistory(sessionId);
          console.log('✅ Loaded history:', history);

          // Convert new history format to message format
          const messages = [];
          if (history && Array.isArray(history)) {
            history.forEach((entry, index) => {
              // New API format has user_message and assistant_response
              if (entry.user_message) {
                messages.push({
                  id: `${entry.message_id || index}-user`,
                  type: 'user',
                  content: entry.user_message,
                  timestamp: entry.timestamp,
                });
              }
              if (entry.assistant_response) {
                messages.push({
                  id: `${entry.message_id || index}-bot`,
                  type: 'bot',
                  content: entry.assistant_response,
                  timestamp: entry.timestamp,
                  sources: entry.sources || [],
                });
              }
            });
          }

          console.log('📝 Converted messages:', messages.length, 'messages');

          set({
            messages,
            isLoading: false,
          });

        } catch (error) {
          console.error('❌ Failed to load conversation history:', error);
          set({
            isLoading: false,
            error: error.message,
          });
        }
      },

      // Load all conversations (UPDATED for new API)
      loadConversations: async () => {
        set({ isLoadingConversations: true });

        try {
          const conversations = await sessionAPI.listSessions();
          console.log('💬 Loaded conversations:', conversations);
          set({
            conversations: conversations || [],
            isLoadingConversations: false,
          });
        } catch (error) {
          console.error('Failed to load conversations:', error);
          set({
            conversations: [],
            isLoadingConversations: false,
          });
        }
      },

      // Start new conversation (UPDATED - creates proper backend session)
      startNewConversation: async (title = null) => {
        try {
          console.log('🆕 Creating new conversation...');

          // Create session via backend API
          const newSession = await sessionAPI.createSession('default_user', title);

          set({
            currentSessionId: newSession.session_id,
            messages: [],
            error: null,
          });

          // Reload conversations to show new one in sidebar
          await get().loadConversations();

          console.log('✅ New conversation created:', newSession.session_id);
          return newSession;
        } catch (error) {
          console.error('❌ Failed to create new conversation:', error);

          // Fallback to local session if backend fails
          const fallbackSessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
          set({
            currentSessionId: fallbackSessionId,
            messages: [],
            error: null,
          });

          throw error;
        }
      },

      // Delete conversation (UPDATED for new API)
      deleteConversation: async (sessionId) => {
        try {
          console.log('🗑️ Deleting conversation:', sessionId);

          // Delete via backend API
          await sessionAPI.deleteSession(sessionId);

          // Remove from conversations list
          set((state) => ({
            conversations: state.conversations.filter(
              (conv) => conv.session_id !== sessionId
            ),
          }));

          // If it was the current conversation, start new one
          const { currentSessionId } = get();
          if (currentSessionId === sessionId) {
            await get().startNewConversation();
          }

          console.log('✅ Conversation deleted successfully');

        } catch (error) {
          console.error('❌ Failed to delete conversation:', error);
          set({ error: error.message });
        }
      },

      // Rename conversation
      renameConversation: async (sessionId, newTitle) => {
        try {
          // Update locally first for immediate feedback
          set((state) => ({
            conversations: state.conversations.map((conv) =>
              conv.session_id === sessionId
                ? { ...conv, title: newTitle }
                : conv
            ),
          }));

          // TODO: Add API call when backend supports it
          // await chatAPI.renameConversation(sessionId, newTitle);

        } catch (error) {
          console.error('Failed to rename conversation:', error);
          // Revert on error
          get().loadConversations();
          set({ error: error.message });
        }
      },

      // Clear messages (for current conversation)
      clearMessages: () => {
        set({ messages: [], error: null });
      },

      // Clear error
      clearError: () => {
        set({ error: null });
      },

      // Toggle sidebar
      toggleSidebar: () => {
        set((state) => ({ sidebarOpen: !state.sidebarOpen }));
      },

      // Toggle upload modal
      toggleUploadModal: () => {
        set((state) => ({ uploadModalOpen: !state.uploadModalOpen }));
      },

      // Set loading state
      setLoading: (isLoading) => {
        set({ isLoading });
      },

      // Set typing state
      setTyping: (isTyping) => {
        set({ isTyping });
      },
    }),
    {
      name: 'comviva-chat-store',
      partialize: (state) => ({
        currentSessionId: state.currentSessionId,
        messages: state.messages,
        sidebarOpen: state.sidebarOpen,
        conversations: state.conversations,
      }),
    }
  )
);

export default useChatStore;