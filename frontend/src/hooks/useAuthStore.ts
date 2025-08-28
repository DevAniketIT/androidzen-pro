import { create } from 'zustand';
import { persist } from 'zustand/middleware';

import { apiService } from '../services/api';
import { User, LoginCredentials, RegisterCredentials } from '../types';
import { STORAGE_KEYS } from '../utils/constants';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

interface AuthActions {
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (credentials: RegisterCredentials) => Promise<void>;
  logout: () => void;
  updateProfile: (data: Partial<User>) => Promise<void>;
  initializeAuth: () => void;
  clearError: () => void;
  setLoading: (loading: boolean) => void;
}

export type AuthStore = AuthState & AuthActions;

export const useAuthStore = create<AuthStore>()(
  persist(
  (set, _get) => ({
      // Initial state
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      // Actions
      login: async (credentials: LoginCredentials) => {
        try {
          set({ isLoading: true, error: null });

          const response = await apiService.post<{ user: User; token: string }>(
            '/auth/login',
            credentials
          );

          if (response.success && response.data) {
            const { user, token } = response.data;

            // Store token in localStorage
            localStorage.setItem(STORAGE_KEYS.AUTH_TOKEN, token);

            set({
              user,
              token,
              isAuthenticated: true,
              isLoading: false,
              error: null,
            });
          } else {
            throw new Error(response.error || 'Login failed');
          }
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Login failed';
          set({
            isLoading: false,
            error: errorMessage,
            isAuthenticated: false,
            user: null,
            token: null,
          });
          localStorage.removeItem(STORAGE_KEYS.AUTH_TOKEN);
          throw error;
        }
      },

      register: async (credentials: RegisterCredentials) => {
        try {
          set({ isLoading: true, error: null });

          const response = await apiService.post<{ user: User; token: string }>(
            '/auth/register',
            credentials
          );

          if (response.success && response.data) {
            const { user, token } = response.data;

            // Store token in localStorage
            localStorage.setItem(STORAGE_KEYS.AUTH_TOKEN, token);

            set({
              user,
              token,
              isAuthenticated: true,
              isLoading: false,
              error: null,
            });
          } else {
            throw new Error(response.error || 'Registration failed');
          }
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Registration failed';
          set({
            isLoading: false,
            error: errorMessage,
            isAuthenticated: false,
            user: null,
            token: null,
          });
          localStorage.removeItem(STORAGE_KEYS.AUTH_TOKEN);
          throw error;
        }
      },

      logout: () => {
        localStorage.removeItem(STORAGE_KEYS.AUTH_TOKEN);
        set({
          user: null,
          token: null,
          isAuthenticated: false,
          isLoading: false,
          error: null,
        });

        // Call logout endpoint to invalidate token on server
        apiService.post('/auth/logout').catch(console.error);
      },

      updateProfile: async (data: Partial<User>) => {
        try {
          set({ isLoading: true, error: null });

          const response = await apiService.put<User>('/auth/profile', data);

          if (response.success && response.data) {
            set((state) => ({
              user: { ...state.user, ...response.data } as User,
              isLoading: false,
              error: null,
            }));
          } else {
            throw new Error(response.error || 'Profile update failed');
          }
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Profile update failed';
          set({ isLoading: false, error: errorMessage });
          throw error;
        }
      },

      initializeAuth: () => {
        const token = localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);

        if (token) {
          set({ isLoading: true });

          // Verify token and get user data
          apiService
            .get<User>('/auth/me')
            .then((response) => {
              if (response.success && response.data) {
                set({
                  user: response.data,
                  token,
                  isAuthenticated: true,
                  isLoading: false,
                  error: null,
                });
              } else {
                // Token is invalid
                localStorage.removeItem(STORAGE_KEYS.AUTH_TOKEN);
                set({
                  user: null,
                  token: null,
                  isAuthenticated: false,
                  isLoading: false,
                  error: null,
                });
              }
            })
            .catch((_error) => {
              // Token verification failed
              localStorage.removeItem(STORAGE_KEYS.AUTH_TOKEN);
              set({
                user: null,
                token: null,
                isAuthenticated: false,
                isLoading: false,
                error: null,
              });
            });
        } else {
          set({ isLoading: false });
        }
      },

      clearError: () => set({ error: null }),

      setLoading: (loading: boolean) => set({ isLoading: loading }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
