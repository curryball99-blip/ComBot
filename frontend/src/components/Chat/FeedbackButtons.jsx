import React, { useState } from 'react';
import { ThumbsUp, ThumbsDown } from 'lucide-react';
import { motion } from 'framer-motion';

const FeedbackButtons = ({ messageId, content, onFeedback }) => {
  const [feedback, setFeedback] = useState(null);

  const handleFeedback = (type) => {
    setFeedback(type);
    onFeedback(messageId, type, content);
  };

  return (
    <div className="flex items-center space-x-2">
      <motion.button
        whileTap={{ scale: 0.9 }}
        onClick={() => handleFeedback('like')}
        className={`p-1 transition-colors ${
          feedback === 'like' 
            ? 'text-green-500' 
            : 'text-gray-400 hover:text-green-500'
        }`}
        title="Helpful response"
      >
        <ThumbsUp className="w-3 h-3" />
      </motion.button>
      
      <motion.button
        whileTap={{ scale: 0.9 }}
        onClick={() => handleFeedback('dislike')}
        className={`p-1 transition-colors ${
          feedback === 'dislike' 
            ? 'text-red-500' 
            : 'text-gray-400 hover:text-red-500'
        }`}
        title="Not helpful"
      >
        <ThumbsDown className="w-3 h-3" />
      </motion.button>
    </div>
  );
};

export default FeedbackButtons;