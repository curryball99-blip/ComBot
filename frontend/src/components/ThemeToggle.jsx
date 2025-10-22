import React from 'react';
import { Sun, Moon } from 'lucide-react';
import { motion } from 'framer-motion';
import useThemeStore from '../stores/themeStore';

const ThemeToggle = ({ className = "" }) => {
  const { isDark, toggleTheme } = useThemeStore();

  return (
    <button
      onClick={toggleTheme}
      className={`
        relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 
        ${isDark ? 'bg-comviva-primary' : 'bg-gray-300'}
        ${className}
      `}
      aria-label="Toggle theme"
    >
      <motion.div
        className="inline-block h-4 w-4 rounded-full bg-white shadow-md"
        animate={{
          x: isDark ? 24 : 4
        }}
        transition={{ type: "spring", stiffness: 500, damping: 30 }}
      >
        <div className="flex items-center justify-center h-full w-full">
          {isDark ? (
            <Moon className="h-2.5 w-2.5 text-comviva-primary" />
          ) : (
            <Sun className="h-2.5 w-2.5 text-amber-500" />
          )}
        </div>
      </motion.div>
    </button>
  );
};

export default ThemeToggle;