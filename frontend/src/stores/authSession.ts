export type AuthStatus = 'authenticated' | 'unauthenticated';

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  profileImage?: string;
}

export interface AuthSnapshot {
  isAuthenticated: boolean;
  status: AuthStatus;
  user: AuthUser | null;
}

interface JwtPayload {
  exp?: number;
}

interface StorageLike {
  getItem(key: string): string | null;
}

const DEFAULT_AUTH_USER: AuthUser = {
  id: 'ssafy-user',
  email: '',
  name: '',
};

function unauthenticatedSnapshot(): AuthSnapshot {
  return {
    isAuthenticated: false,
    status: 'unauthenticated',
    user: null,
  };
}

function authenticatedSnapshot(user: AuthUser | null | undefined): AuthSnapshot {
  return {
    isAuthenticated: true,
    status: 'authenticated',
    user: user ?? DEFAULT_AUTH_USER,
  };
}

function getLocalStorage(): StorageLike | null {
  if (typeof localStorage === 'undefined') {
    return null;
  }

  return localStorage;
}

function decodeBase64Url(value: string) {
  const normalized = value.replace(/-/g, '+').replace(/_/g, '/');
  const padding = normalized.length % 4;
  const withPadding = padding === 0 ? normalized : `${normalized}${'='.repeat(4 - padding)}`;

  if (typeof globalThis.atob !== 'function') {
    throw new Error('base64-decoder-unavailable');
  }

  return globalThis.atob(withPadding);
}

function parseJwtPayload(token: string): JwtPayload | null {
  const [, payload] = token.split('.');
  if (!payload) {
    return null;
  }

  try {
    return JSON.parse(decodeBase64Url(payload)) as JwtPayload;
  } catch {
    return null;
  }
}

function isTokenExpired(token: string) {
  const payload = parseJwtPayload(token);
  if (!payload?.exp) {
    return true;
  }

  return payload.exp <= Math.floor(Date.now() / 1000);
}

export function resolveStoredSession(
  accessToken: string | null,
  _refreshToken: string | null,
) {
  if (!accessToken) {
    return false;
  }

  return !isTokenExpired(accessToken);
}

export function readStoredSession(
  accessTokenKey: string,
  refreshTokenKey: string,
  storage: StorageLike | null = getLocalStorage(),
) {
  if (!storage) {
    return false;
  }

  return resolveStoredSession(
    storage.getItem(accessTokenKey),
    storage.getItem(refreshTokenKey),
  );
}

export function resolveAuthSnapshot(
  persistedSnapshot: Partial<AuthSnapshot> | undefined,
  hasStoredSession: boolean,
): AuthSnapshot {
  if (hasStoredSession) {
    return authenticatedSnapshot(persistedSnapshot?.user);
  }

  return unauthenticatedSnapshot();
}
