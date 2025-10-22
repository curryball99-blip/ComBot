import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Sun, Moon, ZoomIn, ZoomOut, RotateCcw, Brain, Sliders, MessageSquare } from 'lucide-react';
import useThemeStore from '../../stores/themeStore';
import useSettingsStore from '../../stores/settingsStore';

const SettingsModal = ({ isOpen, onClose }) => {
  const { isDark, toggleTheme } = useThemeStore();
  const { 
    zoomLevel, setZoomLevel, resetZoom,
    temperature, setTemperature,
    maxTokens, setMaxTokens,
    topP, setTopP,
    model, setModel,
    customSystemPrompt, setCustomSystemPrompt,
    useCustomPrompt, setUseCustomPrompt,
    resetAISettings
  } = useSettingsStore();
  
  const [activeTab, setActiveTab] = useState('display');
  
  const availableModels = [
    'llama-3.3-70b-versatile',
    'llama-3.1-70b-versatile',
    'llama-3.1-8b-instant',
    'mixtral-8x7b-32768',
    'gemma2-9b-it'
  ];

  const zoomOptions = [
    { value: 0.8, label: '80%' },
    { value: 0.9, label: '90%' },
    { value: 1.0, label: '100%' },
    { value: 1.1, label: '110%' },
    { value: 1.2, label: '120%' },
    { value: 1.3, label: '130%' }
  ];

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-gray-900/50 z-50"
          />
          
          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-full max-w-md bg-white dark:bg-dark-surface rounded-xl shadow-2xl z-50 border border-gray-200 dark:border-dark-border"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-dark-border">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-dark-text">Settings</h2>
              <button
                onClick={onClose}
                className="p-1 text-gray-400 hover:text-gray-600 dark:text-dark-muted dark:hover:text-dark-text transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-gray-200 dark:border-dark-border">
              {[
                { id: 'display', label: 'Display', icon: Sun },
                { id: 'ai', label: 'AI Settings', icon: Brain },
                { id: 'prompts', label: 'Prompts', icon: MessageSquare }
              ].map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  onClick={() => setActiveTab(id)}
                  className={`
                    flex items-center space-x-2 px-4 py-3 text-sm font-medium transition-colors
                    ${activeTab === id
                      ? 'text-comviva-primary border-b-2 border-comviva-primary'
                      : 'text-gray-500 dark:text-dark-muted hover:text-gray-700 dark:hover:text-dark-text'
                    }
                  `}
                >
                  <Icon className="w-4 h-4" />
                  <span>{label}</span>
                </button>
              ))}
            </div>

            {/* Content */}
            <div className="p-6 space-y-6 max-h-96 overflow-y-auto">
              {activeTab === 'display' && (
                <>
                  {/* Theme Settings */}
                  <div>
                    <h3 className="text-sm font-medium text-gray-900 dark:text-dark-text mb-3">Appearance</h3>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600 dark:text-dark-muted">Theme</span>
                      <button
                        onClick={toggleTheme}
                        className={`
                          relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 
                          ${isDark ? 'bg-comviva-primary' : 'bg-gray-300'}
                        `}
                      >
                        <motion.div
                          className="inline-block h-4 w-4 rounded-full bg-white shadow-md"
                          animate={{ x: isDark ? 24 : 4 }}
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
                    </div>
                  </div>

                  {/* Zoom Settings */}
                  <div>
                    <h3 className="text-sm font-medium text-gray-900 dark:text-dark-text mb-3">Zoom</h3>
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-600 dark:text-dark-muted">Zoom Level</span>
                        <div className="flex items-center space-x-2">
                          <button
                            onClick={() => setZoomLevel(Math.max(0.8, zoomLevel - 0.1))}
                            disabled={zoomLevel <= 0.8}
                            className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            <ZoomOut className="w-4 h-4" />
                          </button>
                          <span className="text-sm font-medium text-gray-900 dark:text-dark-text min-w-[3rem] text-center">
                            {Math.round(zoomLevel * 100)}%
                          </span>
                          <button
                            onClick={() => setZoomLevel(Math.min(1.3, zoomLevel + 0.1))}
                            disabled={zoomLevel >= 1.3}
                            className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            <ZoomIn className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-3 gap-2">
                        {zoomOptions.map((option) => (
                          <button
                            key={option.value}
                            onClick={() => setZoomLevel(option.value)}
                            className={`
                              px-3 py-1 text-xs rounded-md transition-colors
                              ${zoomLevel === option.value
                                ? 'bg-comviva-primary text-white'
                                : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                              }
                            `}
                          >
                            {option.label}
                          </button>
                        ))}
                      </div>
                      
                      <button
                        onClick={resetZoom}
                        className="flex items-center space-x-2 text-sm text-comviva-primary hover:text-blue-700 transition-colors"
                      >
                        <RotateCcw className="w-4 h-4" />
                        <span>Reset to Default</span>
                      </button>
                    </div>
                  </div>
                </>
              )}

              {activeTab === 'ai' && (
                <>
                  {/* Model Selection */}
                  <div>
                    <h3 className="text-sm font-medium text-gray-900 dark:text-dark-text mb-3">Model</h3>
                    <select
                      value={model}
                      onChange={(e) => setModel(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
                    >
                      {availableModels.map((modelName) => (
                        <option key={modelName} value={modelName}>
                          {modelName}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Temperature */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-sm font-medium text-gray-900 dark:text-dark-text">Temperature</h3>
                      <span className="text-sm text-gray-600 dark:text-dark-muted">{temperature}</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="2"
                      step="0.1"
                      value={temperature}
                      onChange={(e) => setTemperature(parseFloat(e.target.value))}
                      className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
                    />
                    <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
                      <span>Focused (0)</span>
                      <span>Balanced (1)</span>
                      <span>Creative (2)</span>
                    </div>
                  </div>

                  {/* Max Tokens */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-sm font-medium text-gray-900 dark:text-dark-text">Max Tokens</h3>
                      <span className="text-sm text-gray-600 dark:text-dark-muted">{maxTokens}</span>
                    </div>
                    <input
                      type="range"
                      min="100"
                      max="8192"
                      step="100"
                      value={maxTokens}
                      onChange={(e) => setMaxTokens(parseInt(e.target.value))}
                      className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
                    />
                    <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
                      <span>Short (100)</span>
                      <span>Medium (4096)</span>
                      <span>Long (8192)</span>
                    </div>
                  </div>

                  {/* Top P */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-sm font-medium text-gray-900 dark:text-dark-text">Top P</h3>
                      <span className="text-sm text-gray-600 dark:text-dark-muted">{topP}</span>
                    </div>
                    <input
                      type="range"
                      min="0.1"
                      max="1"
                      step="0.05"
                      value={topP}
                      onChange={(e) => setTopP(parseFloat(e.target.value))}
                      className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
                    />
                    <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
                      <span>Precise (0.1)</span>
                      <span>Diverse (1.0)</span>
                    </div>
                  </div>

                  <button
                    onClick={resetAISettings}
                    className="flex items-center space-x-2 text-sm text-comviva-primary hover:text-blue-700 transition-colors"
                  >
                    <RotateCcw className="w-4 h-4" />
                    <span>Reset AI Settings</span>
                  </button>
                </>
              )}

              {activeTab === 'prompts' && (
                <>
                  {/* Custom System Prompt */}
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-sm font-medium text-gray-900 dark:text-dark-text">Custom System Prompt</h3>
                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={useCustomPrompt}
                          onChange={(e) => setUseCustomPrompt(e.target.checked)}
                          className="mr-2"
                        />
                        <span className="text-sm text-gray-600 dark:text-dark-muted">Enable</span>
                      </label>
                    </div>
                    <textarea
                      value={customSystemPrompt}
                      onChange={(e) => setCustomSystemPrompt(e.target.value)}
                      disabled={!useCustomPrompt}
                      placeholder="Enter your custom system prompt here..."
                      className="w-full h-32 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm resize-none disabled:opacity-50 disabled:cursor-not-allowed"
                    />
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                      Custom prompts override the default UNO AI Assistant behavior. Use carefully.
                    </p>
                  </div>
                </>
              )}
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-gray-200 dark:border-dark-border">
              <div className="flex space-x-3">
                <button
                  onClick={() => {
                    resetZoom();
                    resetAISettings();
                  }}
                  className="flex-1 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 py-2 px-4 rounded-lg transition-colors text-sm"
                >
                  Reset All
                </button>
                <button
                  onClick={onClose}
                  className="flex-1 bg-comviva-primary hover:bg-blue-700 text-white py-2 px-4 rounded-lg transition-colors"
                >
                  Done
                </button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

export default SettingsModal;