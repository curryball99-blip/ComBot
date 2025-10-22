import React from 'react';
import { motion } from 'framer-motion';

const QuickResponses = ({ onSelect, show = true }) => {
  const suggestions = [
    { text: "UNO Messaging platform overview" },
    { text: "UNO Firewall security features" },
    { text: "SMS/MMS/RCS capabilities" },
    { text: "Revenue protection benefits" },
    { text: "Integration and APIs" },
    { text: "Deployment architecture" }
  ];

  if (!show) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-wrap justify-center gap-2 mb-4"
    >
      {suggestions.map((suggestion, index) => (
        <motion.button
          key={index}
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: index * 0.1 }}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => onSelect(suggestion.text)}
          className="inline-flex items-center px-3 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-full text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 hover:border-comviva-primary transition-all duration-200 shadow-sm"
        >
          <span>{suggestion.text}</span>
        </motion.button>
      ))}
    </motion.div>
  );
};

export default QuickResponses;