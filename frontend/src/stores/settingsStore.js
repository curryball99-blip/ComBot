import { create } from 'zustand';
import { persist } from 'zustand/middleware';

const useSettingsStore = create(
  persist(
    (set, get) => ({
      // UI Settings
      zoomLevel: 1.0,
      
      // AI Settings
      temperature: 0.4,
      maxTokens: 3072,
      topP: 0.95,
      model: 'llama-3.3-70b-versatile',
      customSystemPrompt: '',
      useCustomPrompt: false,
      
      // Actions
      setZoomLevel: (level) => {
        const clampedLevel = Math.max(0.8, Math.min(1.3, level));
        set({ zoomLevel: clampedLevel });
        
        // Apply zoom using CSS custom property for better control
        document.documentElement.style.setProperty('--zoom-scale', clampedLevel.toString());
        
        // Apply the zoom to the root element
        const rootElement = document.getElementById('root');
        if (rootElement) {
          rootElement.style.transform = `scale(${clampedLevel})`;
          rootElement.style.transformOrigin = 'top left';
          rootElement.style.width = `${100 / clampedLevel}%`;
          rootElement.style.height = `${100 / clampedLevel}%`;
        }
      },
      
      resetZoom: () => {
        get().setZoomLevel(1.0);
        // Also reset any manual styles
        const rootElement = document.getElementById('root');
        if (rootElement) {
          rootElement.style.transform = '';
          rootElement.style.width = '';
          rootElement.style.height = '';
        }
        document.documentElement.style.removeProperty('--zoom-scale');
      },
      
      // AI Settings Actions
      setTemperature: (temp) => set({ temperature: Math.max(0, Math.min(2, temp)) }),
      setMaxTokens: (tokens) => set({ maxTokens: Math.max(100, Math.min(8192, tokens)) }),
      setTopP: (topP) => set({ topP: Math.max(0.1, Math.min(1, topP)) }),
      setModel: (model) => set({ model }),
      setCustomSystemPrompt: (prompt) => set({ customSystemPrompt: prompt }),
      setUseCustomPrompt: (use) => set({ useCustomPrompt: use }),
      
      resetAISettings: () => set({
        temperature: 0.4,
        maxTokens: 3072,
        topP: 0.95,
        model: 'llama-3.3-70b-versatile',
        customSystemPrompt: '',
        useCustomPrompt: false
      }),
      
      // Initialize settings on load
      initializeSettings: () => {
        const { zoomLevel } = get();
        get().setZoomLevel(zoomLevel);
      }
    }),
    {
      name: 'comviva-settings-store',
      partialize: (state) => ({ 
        zoomLevel: state.zoomLevel,
        temperature: state.temperature,
        maxTokens: state.maxTokens,
        topP: state.topP,
        model: state.model,
        customSystemPrompt: state.customSystemPrompt,
        useCustomPrompt: state.useCustomPrompt
      }),
    }
  )
);

export default useSettingsStore;