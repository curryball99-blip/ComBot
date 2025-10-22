import React from 'react';
import { motion } from 'framer-motion';
import { Bot } from 'lucide-react';

const TypingIndicator = () => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="flex items-start space-x-3"
    >
      <div className="w-8 h-8 bg-comviva-secondary rounded-full flex items-center justify-center flex-shrink-0">
        <Bot className="w-4 h-4 text-white" />
      </div>
      <div className="max-w-3xl">
        <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-md px-4 py-3">
          <div className="typing-indicator">
            <div className="typing-dot"></div>
            <div className="typing-dot"></div>
            <div className="typing-dot"></div>
          </div>
        </div>
        <div className="text-xs text-gray-500 mt-1">
          AI is thinking...
        </div>
      </div>
    </motion.div>
  );
};

export default TypingIndicator;