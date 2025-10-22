import { motion } from 'framer-motion';
import { AlertCircle, Globe, Loader2, Send } from 'lucide-react';
import React, { useEffect, useRef } from 'react';
import Disclaimer from './Disclaimer';
import FileUpload from './FileUpload';
import MessageBubble from './MessageBubble';
import QuickResponses from './QuickResponses';
import TypingIndicator from './TypingIndicator';

import useChatStore from '../../stores/chatStore';
import useSettingsStore from '../../stores/settingsStore';
import ComvivaLogo from '../ComvivaLogo';

const ChatInterface = () => {
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const [inputValue, setInputValue] = React.useState('');
  const [internetSearch, setInternetSearch] = React.useState(false);

  const {
    messages,
    isLoading,
    isTyping,
    error,
    currentSessionId,
    sendMessage,
    clearError,
    startNewConversation,
    initialize,
  } = useChatStore();

  const {
    temperature,
    maxTokens,
    topP,
    model,
    customSystemPrompt,
    useCustomPrompt
  } = useSettingsStore();

  // Auto-scroll to bottom only when there are messages and new ones arrive
  useEffect(() => {
    if (messages.length > 0) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    } else {
      // Scroll to top for new/empty chats
      const messagesContainer = messagesEndRef.current?.closest('.overflow-y-auto');
      if (messagesContainer) {
        messagesContainer.scrollTop = 0;
      }
    }
  }, [messages, isTyping]);

  // Initialize store and focus input on mount
  useEffect(() => {
    initialize();
    inputRef.current?.focus();
  }, [initialize]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!inputValue.trim() || isLoading) return;

    const messageText = inputValue.trim();
    setInputValue('');

    // Ensure we have a session - create one if needed
    if (!currentSessionId) {
      try {
        await startNewConversation();
      } catch (error) {
        console.error('Failed to create session:', error);
        // Continue with message - fallback session will be created
      }
    }

    // Prepare AI parameters from settings
    const aiParams = {
      temperature,
      maxTokens,
      topP,
      model,
      customSystemPrompt,
      useCustomPrompt
    };

    await sendMessage(messageText, true, internetSearch, aiParams); // Enable streaming with AI settings
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleQuickResponse = async (text) => {
    // Ensure we have a session - create one if needed
    if (!currentSessionId) {
      try {
        await startNewConversation();
      } catch (error) {
        console.error('Failed to create session:', error);
      }
    }

    // Auto-send the quick response without keeping it in input
    // Prepare AI parameters from settings
    const aiParams = {
      temperature,
      maxTokens,
      topP,
      model,
      customSystemPrompt,
      useCustomPrompt
    };

    sendMessage(text, true, internetSearch, aiParams);
  };



  return (
    <div className="flex flex-col h-full bg-gray-50 dark:bg-dark-bg">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-6 py-6 scrollbar-thin">
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Welcome message for empty chat */}
          {messages.length === 0 && !isLoading && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-center py-12"
            >
              <div className="flex flex-col items-center space-y-4 mb-6">
                <div className="w-20 h-20 rounded-full flex items-center justify-center shadow-lg">
                  <ComvivaLogo variant="orb" className="w-20 h-20" />
                </div>
                <ComvivaLogo variant="full" className="h-8 w-auto" />
              </div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-dark-text mb-3">
                Comviva UNO AI Assistant
              </h2>
              <div className="text-gray-600 dark:text-dark-muted max-w-md mx-auto space-y-2">
                <p className="font-medium">Ready to help with:</p>
                <div className="text-sm space-y-1">
                  <div>• UNO Messaging Solutions</div>
                  <div>• UNO Messaging Firewall</div>
                  <div>• Technical guidance & troubleshooting</div>
                  <div>• Security best practices</div>
                </div>
                <p className="text-comviva-primary font-medium mt-3">What can I help you with today?</p>
              </div>
              <div className="mt-6">
                <QuickResponses onSelect={handleQuickResponse} show={messages.length === 0} />
              </div>
            </motion.div>
          )}

          {/* Error message */}
          {error && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4"
            >
              <div className="flex items-start space-x-3">
                <AlertCircle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
                <div>
                  <h3 className="text-sm font-medium text-red-800">Error</h3>
                  <p className="text-sm text-red-700 mt-1">{error}</p>
                  <button
                    onClick={clearError}
                    className="text-sm text-red-600 hover:text-red-500 mt-2 underline"
                  >
                    Dismiss
                  </button>
                </div>
              </div>
            </motion.div>
          )}

          {/* Messages */}
          {messages.map((message, index) => (
            <MessageBubble
              key={message.id}
              message={message}
              isLast={index === messages.length - 1}
            />
          ))}

          {/* Typing indicator */}
          {isTyping && <TypingIndicator />}

          {/* Scroll anchor */}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="bg-gray-50 dark:bg-dark-bg px-2 py-2">
        <div className="max-w-4xl mx-auto">
          <form onSubmit={handleSubmit} className="relative">
            <div className="flex items-center space-x-2">
              <div className="flex items-center space-x-2">
                <FileUpload
                  sessionId={currentSessionId || 'default'}
                  onDocumentUploaded={(doc) => {
                    console.log('Document uploaded for session:', currentSessionId || 'default', doc);
                  }}
                />
                <button
                  onClick={() => setInternetSearch(!internetSearch)}
                  className={`p-2 rounded-xl transition-colors ${internetSearch
                      ? 'bg-blue-100 text-blue-600 dark:bg-blue-900 dark:text-blue-400'
                      : 'bg-gray-100 text-gray-500 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-400 dark:hover:bg-gray-600'
                    }`}
                  title={internetSearch ? 'Internet search enabled' : 'Enable internet search'}
                >
                  <Globe className="w-5 h-5" />
                </button>
              </div>
              <div className="flex-1">
                <textarea
                  ref={inputRef}
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Type your message here... (Press Enter to send, Shift+Enter for new line)"
                  className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent transition-colors text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400"
                  rows={inputValue.split('\n').length || 1}
                  maxLength={2000}
                  disabled={isLoading}
                />
              </div>
              <button
                type="submit"
                disabled={!inputValue.trim() || isLoading}
                className="bg-blue-600 hover:bg-blue-700 active:bg-blue-800 disabled:bg-gray-300 dark:disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-xl p-2 transition-colors duration-200 flex-shrink-0"
              >
                {isLoading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" strokeWidth={2.5} />
                )}
              </button>
            </div>

            {/* Character count */}
            {inputValue.length > 0 && (
              <div className="text-xs text-gray-500 dark:text-dark-muted mt-2 text-right">
                {inputValue.length}/2000
              </div>
            )}
          </form>
        </div>
      </div>

      {/* Disclaimer */}
      <Disclaimer />
    </div>
  );
};

export default ChatInterface;