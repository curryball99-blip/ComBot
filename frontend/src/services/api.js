// Updated to connect to new LangGraph backend

// Updated to connect to new LangGraph backend - Server deployment configuration

// Updated to connect to new LangGraph backend - Server deployment configuration
// Determine API base URL dynamically when REACT_APP_API_URL not provided.
// Previous logic incorrectly mapped the public IP to "localhost", which broke external access.
// Rule now:
//   1. If explicit REACT_APP_API_URL set -> use it.
//   2. If running on localhost dev -> http://localhost:8000
//   3. Otherwise reuse the current host (public IP or domain) with backend port 8000.
//   4. Support same protocol upgrade if site served via https.
const getApiBaseUrl = () => {
  try {
    const { protocol, hostname } = window.location;
    const isLocal = ['localhost', '127.0.0.1'].includes(hostname);
    if (isLocal || process.env.NODE_ENV === 'development') {
      return 'http://localhost:8000';
    }
    // Use same protocol if https (behind reverse proxy / load balancer)
    const backendProtocol = protocol === 'https:' ? 'https' : 'http';
    return `${backendProtocol}://${hostname}:8000`;
  } catch (e) {
    // Fallback hard-coded default
    return 'http://localhost:8000';
  }
};

const API_BASE_URL = (process.env.REACT_APP_API_URL && process.env.REACT_APP_API_URL.trim()) || getApiBaseUrl();

// Debug logging
if (typeof window !== 'undefined') {
  console.log('🔧 API Configuration:', {
    pageLocation: window.location.href,
    hostname: window.location.hostname,
    apiBaseUrl: API_BASE_URL,
    env: process.env.NODE_ENV,
    explicitEnvVar: !!process.env.REACT_APP_API_URL
  });
}

export const chatAPI = {
  // Main sendMessage method that the chat store expects
  sendMessage: async (message, sessionId = null, streaming = false, useInternetSearch = false, aiParams = {}) => {
    console.log('🚀 sendMessage called with:', { message, sessionId, streaming, useInternetSearch, apiUrl: API_BASE_URL });
    try {
      const requestBody = {
        message,
        session_id: sessionId,
        stream: streaming,
        internet_search: useInternetSearch,
        ...aiParams
      };

      console.log('📡 Making request to:', `${API_BASE_URL}/api/chat`, 'with body:', requestBody);

      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
      });

      console.log('📥 Response status:', response.status, response.statusText);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log('✅ API response:', result);
      return result;
    } catch (error) {
      console.error('❌ Send message API error:', error);
      throw error;
    }
  },

  // Compatibility shim: some UI code expects chatAPI.processStream.
  // For now we don't have a true streaming backend. The store currently calls:
  //   processStream(initialResponse, onChunk, onComplete, onError)
  // where 'initialResponse' is the full JSON returned by sendMessage.
  // We'll emulate streaming by splitting the full response text into word chunks
  // and invoking callbacks. No extra network call (previous shim caused a 2nd POST with
  // wrong argument ordering -> 422).
  processStream: (initial, onChunk, onComplete, onError) => {
    try {
      // Detect signature misuse. If first param is a string, treat as message and do a fallback send.
      if (typeof initial === 'string') {
        console.warn('[processStream] Received string instead of initial response object; performing single non-streaming request.');
        return (async function* () {
          const result = await chatAPI.sendMessage(initial, null, false);
          // Simulate chunking
          const words = (result.response || '').split(/\s+/);
          for (const w of words) {
            if (onChunk) onChunk(w + ' ');
            yield w; // allow for-await consumer
          }
          if (onComplete) onComplete(result);
        })();
      }

      const fullText = initial && typeof initial === 'object' ? (initial.response || '') : '';
      const words = fullText.split(/\s+/).filter(Boolean);

      // Create async generator that yields each "chunk" (word) to satisfy for-await loop in store
      const generator = (async function* () {
        for (const w of words) {
          if (onChunk) onChunk(w + ' ');
          yield w;
        }
        if (onComplete) onComplete(initial);
      })();

      return generator;
    } catch (err) {
      console.error('[processStream] Emulation error', err);
      if (onError) onError(err.message || String(err));
      // Return an empty async generator to keep caller logic safe
      return (async function* () { })();
    }
  },

  chat: async (message, conversationId = null) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message, session_id: conversationId })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Chat API error:', error);
      throw error;
    }
  },

  workflow: async (message, conversationId = null) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/workflow`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message, conversation_id: conversationId })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Workflow API error:', error);
      throw error;
    }
  },

  search: async (query, limit = 10) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/search?query=${encodeURIComponent(query)}&limit=${limit}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Search API error:', error);
      throw error;
    }
  },

  clearConversation: async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/clear-conversation`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Clear conversation error:', error);
      throw error;
    }
  },

  getConversation: async (conversationId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/conversation/${conversationId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Get conversation error:', error);
      throw error;
    }
  }
};

export const systemAPI = {
  health: async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/health`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Health check error:', error);
      throw error;
    }
  },

  getSystemInfo: async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/system/info`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('System info error:', error);
      throw error;
    }
  }
};

// JIRA Dashboard API endpoints
export const jiraAPI = {
  // Live Summary (new)
  getLiveSummary: async (range = '30d') => {
    const response = await fetch(`${API_BASE_URL}/api/jira/live/summary?range=${encodeURIComponent(range)}`);
    if (!response.ok) throw new Error(`Live summary error ${response.status}`);
    return response.json();
  },
  // Live Team Analytics (new)
  getLiveTeam: async () => {
    const response = await fetch(`${API_BASE_URL}/api/jira/live/team`);
    if (!response.ok) throw new Error(`Live team error ${response.status}`);
    return response.json();
  },
  // Live Search (new)
  liveSearch: async (query, limit = 100) => {
    const body = { query, limit };
    const response = await fetch(`${API_BASE_URL}/api/jira/live/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    if (!response.ok) throw new Error(`Live search error ${response.status}`);
    return response.json();
  },
  // --- Legacy below (kept temporarily) ---
  // Dashboard data
  getDashboard: async (dateRange = '30d') => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/jira/dashboard?dateRange=${dateRange}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('JIRA Dashboard API error:', error);
      throw error;
    }
  },

  // Team analytics
  getTeamAnalytics: async (dateRange = '30d') => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/jira/team-analytics?dateRange=${dateRange}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('JIRA Team Analytics API error:', error);
      throw error;
    }
  },

  // Search tickets
  searchTickets: async (query, filters = {}) => {
    try {
      const params = new URLSearchParams({ query, ...filters });
      const response = await fetch(`${API_BASE_URL}/api/jira/search?${params}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('JIRA Search API error:', error);
      throw error;
    }
  },

  // Get member details
  getMemberDetails: async (memberId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/jira/member/${memberId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('JIRA Member Details API error:', error);
      throw error;
    }
  },

  // Filter options
  getFilterOptions: async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/jira/filter-options`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('JIRA Filter Options API error:', error);
      throw error;
    }
  },

  // Analyze ticket with AI
  analyzeTicket: async (ticketKey, options = {}) => {
    try {
      const requestBody = {
        ticket_key: ticketKey,
        max_references: options.maxReferences || 5,
        include_semantic_search: options.includeSemanticSearch !== false,
        analysis_depth: options.analysisDepth || "comprehensive"
      };

      console.log('🔍 Analyzing ticket:', ticketKey, 'with options:', requestBody);

      const response = await fetch(`${API_BASE_URL}/api/jira/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log('✅ Analysis complete:', result);
      return result;
    } catch (error) {
      console.error('❌ JIRA Analyze API error:', error);
      throw error;
    }
  }
};

// Document processing API
export const documentAPI = {
  // Upload and process document
  uploadDocument: async (file, metadata = {}) => {
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('metadata', JSON.stringify(metadata));

      const response = await fetch(`${API_BASE_URL}/api/documents/upload`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Document upload error:', error);
      throw error;
    }
  },

  // Get processing status
  getProcessingStatus: async (taskId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/documents/status/${taskId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Document status error:', error);
      throw error;
    }
  }
};

// Chat Session Management API (NEW)
export const sessionAPI = {
  // Create new chat session
  createSession: async (userId = 'default_user', title = null) => {
    try {
      console.log('📝 Creating new session:', { userId, title });

      const response = await fetch(`${API_BASE_URL}/api/chat/sessions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
          title: title || `Chat ${new Date().toLocaleString()}`
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log('✅ Session created:', result);
      return result;
    } catch (error) {
      console.error('❌ Create session error:', error);
      throw error;
    }
  },

  // List all chat sessions
  listSessions: async (userId = null, limit = 50) => {
    try {
      const params = new URLSearchParams();
      if (userId) params.append('user_id', userId);
      if (limit) params.append('limit', limit.toString());

      const url = `${API_BASE_URL}/api/chat/sessions${params.toString() ? '?' + params.toString() : ''}`;
      console.log('📋 Loading sessions from:', url);

      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log('✅ Sessions loaded:', result);
      return result.sessions || [];
    } catch (error) {
      console.error('❌ List sessions error:', error);
      throw error;
    }
  },

  // Get session info
  getSession: async (sessionId) => {
    try {
      console.log('📄 Getting session info:', sessionId);

      const response = await fetch(`${API_BASE_URL}/api/chat/sessions/${sessionId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log('✅ Session info loaded:', result);
      return result;
    } catch (error) {
      console.error('❌ Get session error:', error);
      throw error;
    }
  },

  // Delete chat session
  deleteSession: async (sessionId) => {
    try {
      console.log('🗑️ Deleting session:', sessionId);

      const response = await fetch(`${API_BASE_URL}/api/chat/sessions/${sessionId}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log('✅ Session deleted:', result);
      return result;
    } catch (error) {
      console.error('❌ Delete session error:', error);
      throw error;
    }
  },

  // Get chat history for session
  getSessionHistory: async (sessionId, limit = 50) => {
    try {
      console.log('📜 Loading session history:', sessionId);

      const response = await fetch(`${API_BASE_URL}/api/chat/sessions/${sessionId}/history?limit=${limit}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log('✅ Session history loaded:', result);
      return result.messages || [];
    } catch (error) {
      console.error('❌ Get session history error:', error);
      throw error;
    }
  }
};

export default {
  chatAPI,
  systemAPI,
  jiraAPI,
  documentAPI,
  sessionAPI
};