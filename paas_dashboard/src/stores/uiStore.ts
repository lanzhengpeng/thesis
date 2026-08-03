import { create } from 'zustand'

const THEME_STORAGE_KEY = 'paas-dashboard-theme'

export type ThemeMode = 'light' | 'dark'

function getStoredTheme(): ThemeMode {
  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY)
    if (stored === 'light' || stored === 'dark') return stored
  } catch { /* localStorage unavailable */ }
  return 'light'
}

export function applyTheme(theme: ThemeMode) {
  if (typeof document === 'undefined') return
  document.documentElement.setAttribute('data-theme', theme)
  document.documentElement.style.colorScheme = theme
}

export function initializeTheme() {
  applyTheme(getStoredTheme())
}

type UIStore = {
  theme: ThemeMode
  conversationSidebarOpen: boolean
  projectFilesOpen: boolean
  detailPanelOpen: boolean

  setTheme: (theme: ThemeMode) => void
  toggleTheme: () => void
  toggleConversationSidebar: () => void
  setConversationSidebarOpen: (open: boolean) => void
  toggleProjectFiles: () => void
  setProjectFilesOpen: (open: boolean) => void
  setDetailPanelOpen: (open: boolean) => void
}

export const useUIStore = create<UIStore>((set) => ({
  theme: getStoredTheme(),
  conversationSidebarOpen: false,
  projectFilesOpen: false,
  detailPanelOpen: false,

  setTheme: (theme) => {
    applyTheme(theme)
    try { localStorage.setItem(THEME_STORAGE_KEY, theme) } catch { /* noop */ }
    set({ theme })
  },

  toggleTheme: () => {
    set((state) => {
      const next = state.theme === 'light' ? 'dark' : 'light'
      applyTheme(next)
      try { localStorage.setItem(THEME_STORAGE_KEY, next) } catch { /* noop */ }
      return { theme: next }
    })
  },

  toggleConversationSidebar: () =>
    set((s) => ({ conversationSidebarOpen: !s.conversationSidebarOpen })),
  setConversationSidebarOpen: (open) => set({ conversationSidebarOpen: open }),

  toggleProjectFiles: () => set((s) => ({ projectFilesOpen: !s.projectFilesOpen })),
  setProjectFilesOpen: (open) => set({ projectFilesOpen: open }),

  setDetailPanelOpen: (open) => set({ detailPanelOpen: open }),
}))
