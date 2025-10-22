import React, { useRef, useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sun, Moon, Sliders, Brain, MessageSquare } from 'lucide-react';
import useThemeStore from '../../stores/themeStore';
import SettingsModal from './SettingsModal';

const SettingsDropdown = ({ isOpen, onClose, buttonRef }) => {
  const dropdownRef = useRef(null);
  const { isDark, toggleTheme } = useThemeStore();
  const [settingsModalOpen, setSettingsModalOpen] = useState(false);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target) &&
          buttonRef.current && !buttonRef.current.contains(event.target)) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen, onClose, buttonRef]);

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          ref={dropdownRef}
          initial={{ opacity: 0, scale: 0.95, y: -10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: -10 }}
          className="settings-dropdown w-48 bg-white dark:bg-dark-surface rounded-lg shadow-xl border border-gray-200 dark:border-dark-border z-50"
        >
          {/* Header */}
          <div className="p-4 border-b border-gray-200 dark:border-dark-border">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-dark-text">Settings</h3>
          </div>

          {/* Content */}
          <div className="p-2">
            {/* Quick Theme Toggle */}
            <div className="flex items-center justify-between p-2 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-md">
              <div className="flex items-center space-x-2">
                {isDark ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
                <span className="text-sm text-gray-600 dark:text-dark-muted">Theme</span>
              </div>
              <button
                onClick={toggleTheme}
                className={`
                  relative inline-flex h-5 w-9 items-center rounded-full transition-colors duration-200 
                  ${isDark ? 'bg-comviva-primary' : 'bg-gray-300'}
                `}
              >
                <motion.div
                  className="inline-block h-3 w-3 rounded-full bg-white shadow-sm"
                  animate={{ x: isDark ? 20 : 4 }}
                  transition={{ type: "spring", stiffness: 500, damping: 30 }}
                />
              </button>
            </div>
            
            {/* Divider */}
            <div className="border-t border-gray-200 dark:border-gray-600 my-2" />
            
            {/* Advanced Settings Button */}
            <button
              onClick={() => {
                setSettingsModalOpen(true);
                onClose();
              }}
              className="w-full flex items-center space-x-2 p-2 text-left hover:bg-gray-50 dark:hover:bg-gray-700 rounded-md transition-colors"
            >
              <Sliders className="w-4 h-4 text-gray-500" />
              <span className="text-sm text-gray-600 dark:text-dark-muted">Advanced Settings</span>
            </button>
            
            <button
              onClick={() => {
                setSettingsModalOpen(true);
                onClose();
              }}
              className="w-full flex items-center space-x-2 p-2 text-left hover:bg-gray-50 dark:hover:bg-gray-700 rounded-md transition-colors"
            >
              <Brain className="w-4 h-4 text-blue-500" />
              <span className="text-sm text-gray-600 dark:text-dark-muted">AI Settings</span>
            </button>
            
            <button
              onClick={() => {
                setSettingsModalOpen(true);
                onClose();
              }}
              className="w-full flex items-center space-x-2 p-2 text-left hover:bg-gray-50 dark:hover:bg-gray-700 rounded-md transition-colors"
            >
              <MessageSquare className="w-4 h-4 text-green-500" />
              <span className="text-sm text-gray-600 dark:text-dark-muted">Custom Prompts</span>
            </button>
          </div>
        </motion.div>
      )}
      
      {/* Settings Modal */}
      <SettingsModal 
        isOpen={settingsModalOpen} 
        onClose={() => setSettingsModalOpen(false)} 
      />
    </AnimatePresence>
  );
};

export default SettingsDropdown;