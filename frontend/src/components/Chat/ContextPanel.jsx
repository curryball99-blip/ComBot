import React, { useState } from 'react';
import { ChevronDown, ChevronUp, FileText, Star } from 'lucide-react';

const ContextPanel = ({ sources = [] }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!sources || sources.length === 0) return null;

  return (
    <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3 mt-2">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center justify-between w-full text-left"
      >
        <div className="flex items-center space-x-2">
          <FileText className="w-4 h-4 text-blue-600" />
          <span className="text-sm font-medium text-blue-800 dark:text-blue-200">
            Why these docs? ({sources.length} sources)
          </span>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-blue-600" />
        ) : (
          <ChevronDown className="w-4 h-4 text-blue-600" />
        )}
      </button>
      
      {isExpanded && (
        <div className="mt-3 space-y-2">
          {sources.slice(0, 12).map((source, index) => (
            <div key={index} className="bg-white dark:bg-gray-800 rounded p-2 text-xs">
              <div className="flex items-center justify-between mb-1">
                <span className="font-medium text-gray-900 dark:text-white">
                  {source.title || source.component || 'Document'}
                </span>
                <div className="flex items-center space-x-1">
                  <Star className="w-3 h-3 text-yellow-500" />
                  <span className="text-gray-600 dark:text-gray-400">
                    {(source.score * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
              <p className="text-gray-600 dark:text-gray-400 line-clamp-2">
                {source.text?.substring(0, 100)}...
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ContextPanel;