import React from 'react';
import { AlertTriangle } from 'lucide-react';

const Disclaimer = () => {
  return (
    <div className="max-w-4xl mx-auto px-6 py-2 border-t border-gray-200 dark:border-dark-border bg-gray-50 dark:bg-dark-bg">
      <div className="flex items-center space-x-2 text-xs text-gray-500 dark:text-gray-400">
        <AlertTriangle className="w-3 h-3 flex-shrink-0" />
        <p>
          <strong>Disclaimer:</strong> AI-generated responses. Consult official Comviva docs for critical decisions.
        </p>
      </div>
    </div>
  );
};

export default Disclaimer;