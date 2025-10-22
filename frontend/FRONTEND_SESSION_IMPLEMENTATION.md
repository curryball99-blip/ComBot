# Frontend Chat Session Management Implementation Guide

## Overview
This guide provides the complete React implementation for proper chat session management to fix the issue where "New Chat" deletes current conversations instead of saving them.

## Key Features to Implement
1. **Auto-save current conversation** before starting new chat
2. **Load and display recent conversations** 
3. **Switch between conversations** seamlessly
4. **Delete conversations** with UI sync to backend
5. **Session persistence** across page refreshes

## Core Components

### 1. Chat Session Hook (`useChatSession.js`)

```javascript
import { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api';

export const useChatSession = () => {
  const [currentSession, setCurrentSession] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  // Load sessions on mount
  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      const response = await fetch(`${API_BASE}/chat/sessions`);
      const data = await response.json();
      setSessions(data.sessions || []);
    } catch (error) {
      console.error('Failed to load sessions:', error);
    }
  };

  const createNewSession = async (title = null) => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/chat/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: 'default_user', // Replace with actual user ID
          title: title || `Chat ${new Date().toLocaleString()}`
        })
      });
      
      const newSession = await response.json();
      setCurrentSession(newSession);
      setMessages([]);
      
      // Refresh sessions list
      await loadSessions();
      
      return newSession;
    } catch (error) {
      console.error('Failed to create session:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const switchToSession = async (sessionId) => {
    try {
      setLoading(true);
      
      // Load session info
      const sessionResponse = await fetch(`${API_BASE}/chat/sessions/${sessionId}`);
      const session = await sessionResponse.json();
      
      // Load messages
      const historyResponse = await fetch(`${API_BASE}/chat/sessions/${sessionId}/history`);
      const history = await historyResponse.json();
      
      setCurrentSession(session);
      setMessages(history.messages || []);
      
    } catch (error) {
      console.error('Failed to switch session:', error);
    } finally {
      setLoading(false);
    }
  };

  const deleteSession = async (sessionId) => {
    try {
      await fetch(`${API_BASE}/chat/sessions/${sessionId}`, {
        method: 'DELETE'
      });
      
      // Remove from local state
      setSessions(prev => prev.filter(s => s.session_id !== sessionId));
      
      // If deleting current session, clear it
      if (currentSession?.session_id === sessionId) {
        setCurrentSession(null);
        setMessages([]);
      }
      
    } catch (error) {
      console.error('Failed to delete session:', error);
      throw error;
    }
  };

  const sendMessage = async (message, temperature = 0.7, model = 'llama-3.3-70b-versatile') => {
    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          session_id: currentSession?.session_id,
          stream: false,
          temperature,
          model
        })
      });
      
      const data = await response.json();
      
      // Add messages to local state
      const userMessage = {
        role: 'user',
        content: message,
        timestamp: new Date().toISOString()
      };
      
      const assistantMessage = {
        role: 'assistant', 
        content: data.response,
        timestamp: data.timestamp,
        sources: data.sources
      };
      
      setMessages(prev => [...prev, userMessage, assistantMessage]);
      
      return data;
    } catch (error) {
      console.error('Failed to send message:', error);
      throw error;
    }
  };

  const handleNewChat = async () => {
    // Key fix: Always create new session, don't clear current one
    return await createNewSession();
  };

  return {
    currentSession,
    sessions,
    messages,
    loading,
    createNewSession,
    switchToSession,
    deleteSession,
    sendMessage,
    handleNewChat,
    loadSessions
  };
};
```

### 2. Session Sidebar Component (`SessionSidebar.jsx`)

```javascript
import React from 'react';
import { formatDistanceToNow } from 'date-fns';

const SessionSidebar = ({ 
  sessions, 
  currentSession, 
  onSelectSession, 
  onDeleteSession, 
  onNewChat,
  loading 
}) => {
  return (
    <div className="w-64 bg-gray-50 border-r border-gray-200 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <button
          onClick={onNewChat}
          disabled={loading}
          className="w-full bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Creating...' : '+ New Chat'}
        </button>
      </div>

      {/* Recent Conversations */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-4">
          <h3 className="text-sm font-medium text-gray-900 mb-3">Recent Conversations</h3>
          
          {sessions.length === 0 ? (
            <div className="text-sm text-gray-500 text-center py-8">
              No conversations yet
            </div>
          ) : (
            <div className="space-y-2">
              {sessions.map((session) => (
                <div
                  key={session.session_id}
                  className={`
                    group relative p-3 rounded-lg cursor-pointer transition-colors
                    ${currentSession?.session_id === session.session_id 
                      ? 'bg-blue-100 border-blue-200 border' 
                      : 'bg-white border border-gray-200 hover:bg-gray-50'
                    }
                  `}
                  onClick={() => onSelectSession(session.session_id)}
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {session.title}
                      </p>
                      <p className="text-xs text-gray-500 truncate mt-1">
                        {session.last_message_preview}
                      </p>
                      <p className="text-xs text-gray-400 mt-1">
                        {formatDistanceToNow(new Date(session.updated_at), { addSuffix: true })}
                      </p>
                    </div>
                    
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteSession(session.session_id);
                      }}
                      className="opacity-0 group-hover:opacity-100 text-red-500 hover:text-red-700 p-1"
                      title="Delete conversation"
                    >
                      🗑️
                    </button>
                  </div>
                  
                  <div className="flex justify-between items-center mt-2">
                    <span className="text-xs text-gray-500">
                      {session.message_count} messages
                    </span>
                    <span className={`
                      text-xs px-2 py-1 rounded-full
                      ${session.status === 'active' 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-gray-100 text-gray-600'
                      }
                    `}>
                      {session.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SessionSidebar;
```

### 3. Updated Main Chat Component (`Chat.jsx`)

```javascript
import React, { useState, useEffect } from 'react';
import SessionSidebar from './SessionSidebar';
import { useChatSession } from './useChatSession';

const Chat = () => {
  const {
    currentSession,
    sessions,
    messages,
    loading,
    switchToSession,
    deleteSession,
    sendMessage,
    handleNewChat
  } = useChatSession();

  const [inputMessage, setInputMessage] = useState('');
  const [sending, setSending] = useState(false);

  // Auto-create first session
  useEffect(() => {
    if (!currentSession && sessions.length === 0 && !loading) {
      handleNewChat();
    }
  }, [currentSession, sessions, loading]);

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || sending) return;
    
    // Create session if none exists
    if (!currentSession) {
      await handleNewChat();
    }

    try {
      setSending(true);
      await sendMessage(inputMessage.trim());
      setInputMessage('');
    } catch (error) {
      console.error('Failed to send message:', error);
      alert('Failed to send message. Please try again.');
    } finally {
      setSending(false);
    }
  };

  const handleDeleteSession = async (sessionId) => {
    if (confirm('Are you sure you want to delete this conversation?')) {
      try {
        await deleteSession(sessionId);
      } catch (error) {
        alert('Failed to delete conversation');
      }
    }
  };

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <SessionSidebar
        sessions={sessions}
        currentSession={currentSession}
        onSelectSession={switchToSession}
        onDeleteSession={handleDeleteSession}
        onNewChat={handleNewChat}
        loading={loading}
      />

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 px-6 py-4">
          <h1 className="text-xl font-semibold text-gray-900">
            {currentSession ? currentSession.title : 'New Chat'}
          </h1>
          {currentSession && (
            <p className="text-sm text-gray-500">
              Session: {currentSession.session_id.slice(0, 8)}...
            </p>
          )}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 ? (
            <div className="text-center text-gray-500 py-12">
              <h3 className="text-lg font-medium mb-2">Start a conversation</h3>
              <p>Ask me anything about your JIRA tickets or documents.</p>
            </div>
          ) : (
            messages.map((message, index) => (
              <div
                key={index}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`
                    max-w-3xl px-4 py-2 rounded-lg
                    ${message.role === 'user' 
                      ? 'bg-blue-600 text-white' 
                      : 'bg-white border border-gray-200'
                    }
                  `}
                >
                  <p className="whitespace-pre-wrap">{message.content}</p>
                  {message.sources && message.sources.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-gray-200">
                      <p className="text-xs text-gray-600 mb-1">Sources:</p>
                      <div className="flex flex-wrap gap-1">
                        {message.sources.map((source, i) => (
                          <span
                            key={i}
                            className="text-xs bg-gray-100 px-2 py-1 rounded"
                          >
                            {source.ticket_key}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Input Area */}
        <div className="bg-white border-t border-gray-200 p-6">
          <div className="flex gap-4">
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
              placeholder="Ask about JIRA tickets, documents, or anything else..."
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={sending}
            />
            <button
              onClick={handleSendMessage}
              disabled={sending || !inputMessage.trim()}
              className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {sending ? 'Sending...' : 'Send'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Chat;
```

### 4. Installation Requirements

Add these dependencies to your `package.json`:

```json
{
  "dependencies": {
    "date-fns": "^2.30.0"
  }
}
```

Install with:
```bash
npm install date-fns
```

## Key Implementation Points

### ✅ Fixed Issues
1. **"New Chat" now preserves conversations**: The `handleNewChat()` function creates a new session without clearing the current one
2. **Automatic session creation**: Sessions are created automatically when needed
3. **Proper session switching**: Users can switch between conversations seamlessly 
4. **UI sync with backend**: Deletions are properly synced between frontend and backend
5. **Conversation persistence**: All conversations are stored and can be resumed

### ✅ Features Implemented
- **Auto-save**: Conversations are automatically saved to Qdrant via the chat API
- **Recent conversations sidebar**: Shows all saved conversations with previews
- **Session management**: Full CRUD operations on chat sessions
- **Message history**: Complete conversation history loading
- **Real-time updates**: Session list updates after operations

### 🔄 How It Works
1. When user clicks "New Chat", a new session is created via POST `/api/chat/sessions`
2. Current conversation remains in the sidebar under "Recent Conversations"
3. Messages are automatically linked to the current session via `session_id`
4. Users can switch between conversations by clicking them in the sidebar
5. Deletions call DELETE `/api/chat/sessions/{id}` and update the UI

## Testing the Implementation

1. **Test New Chat**: Click "New Chat" multiple times - each should create a separate conversation
2. **Test Session Switching**: Switch between conversations in the sidebar
3. **Test Persistence**: Refresh the page - conversations should remain
4. **Test Deletion**: Delete conversations and verify they're removed from backend

Your backend is already fully implemented and tested - this frontend code will complete the integration!