import { create } from 'zustand';
import { persist } from 'zustand/middleware';

const useThemeStore = create(
  persist(
    (set, get) => ({
      // Theme state
      isDark: false,
      
      // Actions
      toggleTheme: () => {
        const newTheme = !get().isDark;
        set({ isDark: newTheme });
        
        // Apply theme to document
        if (newTheme) {
          document.documentElement.classList.add('dark');
        } else {
          document.documentElement.classList.remove('dark');
        }
      },
      
      setTheme: (isDark) => {
        set({ isDark });
        
        // Apply theme to document
        if (isDark) {
          document.documentElement.classList.add('dark');
        } else {
          document.documentElement.classList.remove('dark');
        }
      },
      
      // Initialize theme on load
      initializeTheme: () => {
        const { isDark } = get();
        
        // Check system preference if no saved preference
        if (isDark === null) {
          const systemPrefersDark = window.matchMedia && 
            window.matchMedia('(prefers-color-scheme: dark)').matches;
          set({ isDark: systemPrefersDark });
        }
        
        // Apply initial theme
        if (get().isDark) {
          document.documentElement.classList.add('dark');
        } else {
          document.documentElement.classList.remove('dark');
        }
      }
    }),
    {
      name: 'comviva-theme-store',
      partialize: (state) => ({ isDark: state.isDark }),
    }
  )
);

export default useThemeStore;