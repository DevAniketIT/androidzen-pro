import { create } from 'zustand';
import { persist } from 'zustand/middleware';

import { AppStore, Device, SystemAlert, ThemeConfig } from '../types';

export const useAppStore = create<AppStore>()(
  persist(
  (set, _get) => ({
      // Theme state
      theme: {
        mode: 'dark',
        primaryColor: '#4CAF50',
        secondaryColor: '#FF9800',
        sidebarCollapsed: false,
      },

      setTheme: (theme: Partial<ThemeConfig>) =>
        set((state) => ({
          theme: { ...state.theme, ...theme },
        })),

      toggleSidebar: () =>
        set((state) => ({
          theme: { ...state.theme, sidebarCollapsed: !state.theme.sidebarCollapsed },
        })),

      // Notifications
      notifications: [],

      addNotification: (notification: Omit<SystemAlert, 'id' | 'timestamp' | 'isRead'>) =>
        set((state) => ({
          notifications: [
            ...state.notifications,
            {
              ...notification,
              id: Math.random().toString(36).substr(2, 9),
              timestamp: new Date().toISOString(),
              isRead: false,
            },
          ],
        })),

      removeNotification: (id: string) =>
        set((state) => ({
          notifications: state.notifications.filter((n) => n.id !== id),
        })),

      markNotificationAsRead: (id: string) =>
        set((state) => ({
          notifications: state.notifications.map((n) => (n.id === id ? { ...n, isRead: true } : n)),
        })),

      clearNotifications: () => set({ notifications: [] }),

      // WebSocket connection status
      isConnected: false,

      setConnectionStatus: (connected: boolean) => set({ isConnected: connected }),

      // Device selection
      selectedDevice: null,

      setSelectedDevice: (device: Device | null) => set({ selectedDevice: device }),
    }),
    {
      name: 'app-storage',
      partialize: (state) => ({
        theme: state.theme,
        selectedDevice: state.selectedDevice,
      }),
    }
  )
);
