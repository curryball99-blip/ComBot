import React from 'react';
import { motion } from 'framer-motion';
import { Sun, Moon, ZoomIn, ZoomOut, RotateCcw, Brain, Sliders, MessageSquare } from 'lucide-react';
import useThemeStore from '../stores/themeStore';
import useSettingsStore from '../stores/settingsStore';

const SettingsPage = () => {
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
    <div className="flex-1 overflow-y-auto bg-gray-50 dark:bg-dark-bg">
      <div className="max-w-4xl mx-auto p-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-8"
        >
          {/* Header */}
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-dark-text mb-2">Settings</h1>
            <p className="text-gray-600 dark:text-dark-muted">Customize your AI assistant experience</p>
          </div>

          {/* Display Settings */}
          <div className="bg-white dark:bg-dark-surface rounded-xl shadow-sm border border-gray-200 dark:border-dark-border p-6">
            <div className="flex items-center space-x-3 mb-6">
              <Sun className="w-5 h-5 text-amber-500" />
              <h2 className="text-lg font-semibold text-gray-900 dark:text-dark-text">Display</h2>
            </div>
            
            <div className="space-y-6">
              {/* Theme */}
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-medium text-gray-900 dark:text-dark-text">Theme</h3>
                  <p className="text-sm text-gray-500 dark:text-dark-muted">Choose your preferred color scheme</p>
                </div>
                <button
                  onClick={toggleTheme}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 ${isDark ? 'bg-comviva-primary' : 'bg-gray-300'}`}
                >
                  <motion.div
                    className="inline-block h-4 w-4 rounded-full bg-white shadow-md"
                    animate={{ x: isDark ? 24 : 4 }}
                    transition={{ type: "spring", stiffness: 500, damping: 30 }}
                  >
                    <div className="flex items-center justify-center h-full w-full">
                      {isDark ? <Moon className="h-2.5 w-2.5 text-comviva-primary" /> : <Sun className="h-2.5 w-2.5 text-amber-500" />}
                    </div>
                  </motion.div>
                </button>
              </div>

              {/* Zoom */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h3 className="text-sm font-medium text-gray-900 dark:text-dark-text">Zoom Level</h3>
                    <p className="text-sm text-gray-500 dark:text-dark-muted">Adjust interface size</p>
                  </div>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => setZoomLevel(Math.max(0.8, zoomLevel - 0.1))}
                      disabled={zoomLevel <= 0.8}
                      className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-50"
                    >
                      <ZoomOut className="w-4 h-4" />
                    </button>
                    <span className="text-sm font-medium text-gray-900 dark:text-dark-text min-w-[3rem] text-center">
                      {Math.round(zoomLevel * 100)}%
                    </span>
                    <button
                      onClick={() => setZoomLevel(Math.min(1.3, zoomLevel + 0.1))}
                      disabled={zoomLevel >= 1.3}
                      className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-50"
                    >
                      <ZoomIn className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                
                <div className="grid grid-cols-6 gap-2 mb-3">
                  {zoomOptions.map((option) => (
                    <button
                      key={option.value}
                      onClick={() => setZoomLevel(option.value)}
                      className={`px-3 py-1 text-xs rounded-md transition-colors ${
                        zoomLevel === option.value
                          ? 'bg-comviva-primary text-white'
                          : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                      }`}
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
          </div>

          {/* AI Settings */}
          <div className="bg-white dark:bg-dark-surface rounded-xl shadow-sm border border-gray-200 dark:border-dark-border p-6">
            <div className="flex items-center space-x-3 mb-6">
              <Brain className="w-5 h-5 text-blue-500" />
              <h2 className="text-lg font-semibold text-gray-900 dark:text-dark-text">AI Parameters</h2>
            </div>
            
            <div className="space-y-6">
              {/* Model Selection */}
              <div>
                <h3 className="text-sm font-medium text-gray-900 dark:text-dark-text mb-2">Model</h3>
                <select
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                >
                  {availableModels.map((modelName) => (
                    <option key={modelName} value={modelName}>{modelName}</option>
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
            </div>
          </div>

          {/* Custom Prompts */}
          <div className="bg-white dark:bg-dark-surface rounded-xl shadow-sm border border-gray-200 dark:border-dark-border p-6">
            <div className="flex items-center space-x-3 mb-6">
              <MessageSquare className="w-5 h-5 text-green-500" />
              <h2 className="text-lg font-semibold text-gray-900 dark:text-dark-text">System Prompts</h2>
            </div>
            
            <div className="space-y-6">
              {/* Current Default Prompt */}
              <div>
                <h3 className="text-sm font-medium text-gray-900 dark:text-dark-text mb-2">Current Default Prompt</h3>
                <div className="bg-gray-50 dark:bg-gray-800 rounded-md p-3 max-h-32 overflow-y-auto text-xs text-gray-600 dark:text-gray-400">
                  You are Comviva UNO AI Assistant - a knowledgeable expert in UNO Messaging Solutions and UNO Messaging Firewall.
                  <br/><br/>
                  <strong>Your Role:</strong><br/>
                  Provide comprehensive, detailed, and actionable guidance on UNO products. Be thorough in explanations while maintaining clarity.
                  <br/><br/>
                  <strong>Response Guidelines:</strong><br/>
                  • Provide detailed explanations with step-by-step guidance<br/>
                  • Include specific examples, configurations, and best practices<br/>
                  • Explain technical concepts clearly with context<br/>
                  • Use bullet points, numbered lists, and clear formatting
                </div>
              </div>
              
              {/* Custom Prompt Toggle */}
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-medium text-gray-900 dark:text-dark-text">Enable Custom Prompt</h3>
                  <p className="text-sm text-gray-500 dark:text-dark-muted">
                    {useCustomPrompt ? 'Using custom prompt' : 'Using default UNO AI Assistant prompt'}
                  </p>
                </div>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={useCustomPrompt}
                    onChange={(e) => setUseCustomPrompt(e.target.checked)}
                    className="mr-2"
                  />
                </label>
              </div>
              
              {/* Custom Prompt Editor */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-medium text-gray-900 dark:text-dark-text">Your Custom Prompt</h3>
                  {customSystemPrompt && (
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      {customSystemPrompt.length} characters
                    </span>
                  )}
                </div>
                <textarea
                  value={customSystemPrompt}
                  onChange={(e) => setCustomSystemPrompt(e.target.value)}
                  placeholder="Enter your custom system prompt here... (Your text will be preserved even when disabled)"
                  className="w-full h-32 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white resize-none text-sm"
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                  💡 Your custom prompt is always preserved. Toggle above to switch between default and custom behavior.
                </p>
              </div>
            </div>
          </div>

          {/* Reset All */}
          <div className="flex justify-center">
            <button
              onClick={() => {
                resetZoom();
                resetAISettings();
              }}
              className="bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 py-2 px-6 rounded-lg transition-colors"
            >
              Reset All Settings
            </button>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default SettingsPage;