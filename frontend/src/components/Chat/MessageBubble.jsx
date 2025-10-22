import React from 'react';
import { motion } from 'framer-motion';
import { User, Bot, Copy, ExternalLink, AlertCircle } from 'lucide-react';
import { format } from 'date-fns';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { tomorrow } from 'react-syntax-highlighter/dist/esm/styles/prism';
import ChartRenderer from '../Charts/ChartRenderer';
import UNODashboard from '../Charts/UNODashboard';
import FeedbackButtons from './FeedbackButtons';

const MessageBubble = ({ message, isLast }) => {
  const [copied, setCopied] = React.useState(false);

  const handleFeedback = async (messageId, type, content) => {
    try {
      await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messageId, type, content })
      });
    } catch (error) {
      console.error('Feedback error:', error);
    }
  };

  const handleCopy = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy text:', err);
    }
  };

  const formatTimestamp = (timestamp) => {
    try {
      return format(new Date(timestamp), 'MMM d, h:mm a');
    } catch {
      return '';
    }
  };

  const messageVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 },
  };

  if (message.type === 'user') {
    return (
      <motion.div
        variants={messageVariants}
        initial="hidden"
        animate="visible"
        transition={{ duration: 0.3 }}
        className="flex justify-end items-start space-x-3"
      >
        <div className="max-w-3xl">
          <div className="user-message">
            <div className="whitespace-pre-wrap break-words">
              {message.content}
            </div>
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400 text-right mt-1">
            {formatTimestamp(message.timestamp)}
          </div>
        </div>
        <div className="w-8 h-8 bg-comviva-primary rounded-full flex items-center justify-center flex-shrink-0">
          <User className="w-4 h-4 text-white" />
        </div>
      </motion.div>
    );
  }

  if (message.type === 'error') {
    return (
      <motion.div
        variants={messageVariants}
        initial="hidden"
        animate="visible"
        transition={{ duration: 0.3 }}
        className="flex items-start space-x-3"
      >
        <div className="w-8 h-8 bg-red-500 rounded-full flex items-center justify-center flex-shrink-0">
          <AlertCircle className="w-4 h-4 text-white" />
        </div>
        <div className="max-w-3xl">
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-2xl rounded-tl-md px-4 py-3">
            <div className="text-red-800 dark:text-red-200 whitespace-pre-wrap break-words">
              {message.content}
            </div>
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {formatTimestamp(message.timestamp)}
          </div>
        </div>
      </motion.div>
    );
  }

  // Bot message
  return (
    <motion.div
      variants={messageVariants}
      initial="hidden"
      animate="visible"
      transition={{ duration: 0.3 }}
      className="flex items-start space-x-3"
    >
      <div className="w-8 h-8 bg-comviva-secondary rounded-full flex items-center justify-center flex-shrink-0">
        <Bot className="w-4 h-4 text-white" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-2xl rounded-tl-md px-4 py-3 max-w-none overflow-hidden shadow-sm">
          <div className="markdown-content prose prose-sm max-w-none break-words overflow-wrap-anywhere text-gray-800 dark:text-gray-200">
            {/* Show typing indicator if streaming but no content yet */}
            {message.isStreaming && !message.content ? (
              <div className="flex items-center space-x-1 text-gray-500">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                </div>
                <span className="text-sm">Thinking...</span>
              </div>
            ) : (
              <ReactMarkdown
                components={{
                  code({ node, inline, className, children, ...props }) {
                    const match = /language-(\w+)/.exec(className || '');
                    return !inline && match ? (
                      <SyntaxHighlighter
                        style={tomorrow}
                        language={match[1]}
                        PreTag="div"
                        className="rounded-lg !mt-2 !mb-2 text-sm"
                        {...props}
                      >
                        {String(children).replace(/\n$/, '')}
                      </SyntaxHighlighter>
                    ) : (
                      <code className="bg-gray-100 dark:bg-gray-700 text-comviva-primary dark:text-blue-400 px-1.5 py-0.5 rounded text-sm font-mono" {...props}>
                        {children}
                      </code>
                    );
                  },
                  a({ children, href, ...props }) {
                    return (
                      <a
                        href={href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-comviva-primary hover:text-blue-700 underline inline-flex items-center gap-1 font-medium"
                        {...props}
                      >
                        {children}
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    );
                  },
                  p({ children }) {
                    return <p className="mb-2 leading-relaxed">{children}</p>;
                  },
                  ul({ children }) {
                    return <ul className="mb-2 ml-4 space-y-1">{children}</ul>;
                  },
                  ol({ children }) {
                    return <ol className="mb-2 ml-4 space-y-1">{children}</ol>;
                  },
                  li({ children }) {
                    return <li className="text-gray-700 dark:text-gray-300">{children}</li>;
                  },
                  strong({ children }) {
                    return <strong className="font-semibold text-gray-900 dark:text-white">{children}</strong>;
                  },
                  h1({ children }) {
                    return <h1 className="text-lg font-semibold text-gray-900 dark:text-white mb-2 mt-3">{children}</h1>;
                  },
                  h2({ children }) {
                    return <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-2 mt-3">{children}</h2>;
                  },
                  h3({ children }) {
                    return <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-1 mt-2">{children}</h3>;
                  },
                  blockquote({ children }) {
                    return (
                      <blockquote className="border-l-4 border-comviva-primary pl-4 py-2 bg-blue-50 dark:bg-blue-900/20 rounded-r-lg mb-2 italic">
                        {children}
                      </blockquote>
                    );
                  },
                  table({ children }) {
                    return (
                      <div className="overflow-x-auto my-4">
                        <table className="min-w-full border border-gray-200 dark:border-gray-600 rounded-lg">
                          {children}
                        </table>
                      </div>
                    );
                  },
                  thead({ children }) {
                    return <thead className="bg-gray-50 dark:bg-gray-700">{children}</thead>;
                  },
                  tbody({ children }) {
                    return <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-600">{children}</tbody>;
                  },
                  tr({ children }) {
                    return <tr>{children}</tr>;
                  },
                  th({ children }) {
                    return (
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-900 dark:text-white uppercase tracking-wider border-b border-gray-200 dark:border-gray-600">
                        {children}
                      </th>
                    );
                  },
                  td({ children }) {
                    return (
                      <td className="px-4 py-3 text-sm text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-gray-600">
                        {children}
                      </td>
                    );
                  },
                }}
              >
                {message.content}
              </ReactMarkdown>
            )}
          </div>
          

        </div>
        
        <div className="flex items-center justify-between mt-2">
          <div className="text-xs text-gray-500 dark:text-gray-400">
            {formatTimestamp(message.timestamp)}
          </div>
          <div className="flex items-center space-x-3">
            <FeedbackButtons 
              messageId={message.id}
              content={message.content}
              onFeedback={handleFeedback}
            />
            <button
              onClick={() => handleCopy(message.content)}
              className="text-xs text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 flex items-center space-x-1 transition-colors"
            >
              <Copy className="w-3 h-3" />
              <span>{copied ? 'Copied!' : 'Copy'}</span>
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default MessageBubble;