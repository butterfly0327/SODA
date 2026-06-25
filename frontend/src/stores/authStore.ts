import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { getAuthStorageKeys } from '@/app/lib/authNavigation';
import { authApi } from '@/api/authApi';
import {
  readStoredSession,
  resolveAuthSnapshot,
  type AuthStatus,
  type AuthUser,
} from './authSession';
import { syncChatStoreToCurrentSession } from './chatStore';
import { resetCommunityStore } from './communityStore';
import { resetResourceReviewStore } from './resourceReviewStore';
import { shouldResetUiStateForAuthTransition } from './uiStateIsolation';
import { clearSsafyConsent } from '@/app/lib/ssafyLoginFlow';

const {
  accessToken: ACCESS_TOKEN_KEY,
  refreshToken: REFRESH_TOKEN_KEY,
  storage: AUTH_STORAGE_KEY,
} = getAuthStorageKeys();

const initialAuthSnapshot = resolveAuthSnapshot(
  undefined,
  readStoredSession(ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY),
);

function sanitizeUser(user: AuthUser | null | undefined): AuthUser | null {
  if (!user) {
    return null;
  }

  if (user.name !== 'SSAFY 사용자') {
    return user;
  }

  return {
    ...user,
    name: '',
  };
}

interface AuthState {
  isAuthenticated: boolean;
  status: AuthStatus;
  user: AuthUser | null;
  error: string | null;
  justWithdrew: boolean;
  oauthLoginSuccess: (payload: {
    accessToken?: string;
    refreshToken?: string;
    user?: AuthUser;
  }) => void;
  oauthLoginFail: (message: string) => void;
  logout: () => Promise<void>;
  setJustWithdrew: (withdrew: boolean) => void;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => {
      const resetUserScopedUiState = () => {
        resetCommunityStore();
        resetResourceReviewStore();
      };

      const resetAuthScopedUiState = () => {
        resetCommunityStore();
        resetResourceReviewStore();
      };

      const clearAuthState = (error: string | null = null, clearConsent = false) => {
        localStorage.removeItem(ACCESS_TOKEN_KEY);
        localStorage.removeItem(REFRESH_TOKEN_KEY);
        if (clearConsent) {
          clearSsafyConsent();
        }
        set({
          isAuthenticated: false,
          status: 'unauthenticated',
          user: null,
          error,
          justWithdrew: false,
        });
        resetAuthScopedUiState();
        void syncChatStoreToCurrentSession();
      };

      return {
      ...initialAuthSnapshot,
      error: null,
      justWithdrew: false,
      oauthLoginSuccess: ({ accessToken, refreshToken, user }) => {
        if (!accessToken) {
          clearAuthState('로그인 토큰을 확인할 수 없습니다. 다시 로그인해주세요.');
          return;
        }

        const resolvedUser: AuthUser =
          user ?? {
            id: 'ssafy-user',
            email: '',
            name: '',
          };
        const previousUserId = get().user?.id ?? null;
        const nextUserId = resolvedUser.id ?? null;

        localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);

        if (refreshToken) {
          localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
        } else {
          localStorage.removeItem(REFRESH_TOKEN_KEY);
        }

        set({
          isAuthenticated: true,
          status: 'authenticated',
          user: sanitizeUser(resolvedUser),
          error: null,
        });

        void syncChatStoreToCurrentSession();

        if (shouldResetUiStateForAuthTransition(previousUserId, nextUserId)) {
          resetUserScopedUiState();
        }
      },
      oauthLoginFail: (message: string) => {
        clearAuthState(message);
      },
      logout: async () => {
        const shouldClearConsent = get().justWithdrew;
        try {
          await authApi.logout();
        } catch {
        } finally {
          clearAuthState(null, shouldClearConsent);
        }
      },
      setJustWithdrew: (withdrew: boolean) =>
        set({ justWithdrew: withdrew }),
      clearError: () => set({ error: null }),
    };
    },
    {
      name: AUTH_STORAGE_KEY,
      partialize: (state) => ({
        isAuthenticated: state.isAuthenticated,
        status: state.status,
        user: state.user,
        justWithdrew: state.justWithdrew,
      }),
      merge: (persistedState, currentState) => {
        const persistedAuthState = persistedState as Partial<AuthState> | undefined;
        const resolvedAuthSnapshot = resolveAuthSnapshot(
          persistedAuthState
            ? {
                isAuthenticated: persistedAuthState.isAuthenticated,
                status: persistedAuthState.status,
                user: sanitizeUser(persistedAuthState.user ?? null),
              }
            : undefined,
          readStoredSession(ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY),
        );

        return {
          ...currentState,
          ...persistedAuthState,
          ...resolvedAuthSnapshot,
        };
      },
    }
  )
);
