import axios, { AxiosError } from 'axios';
import type { InternalAxiosRequestConfig } from 'axios';
import {
  getAuthStorageKeys,
  toAppRelativePath,
} from '@/app/lib/authNavigation';
import { beginSsafyLoginFlow } from '@/app/lib/ssafyLoginFlow';

const apiBaseUrl =
  import.meta.env.VITE_API_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  '/api/v1';

const { accessToken: ACCESS_TOKEN_KEY, refreshToken: REFRESH_TOKEN_KEY } =
  getAuthStorageKeys();

interface ApiResponse<T> {
  status: number;
  message: string;
  data: T;
}

interface ReissuePayload {
  accessToken: string;
}

interface RetryableRequestConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

// axios 인스턴스 생성
export const apiClient = axios.create({
  baseURL: apiBaseUrl,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

const reissueClient = axios.create({
  baseURL: apiBaseUrl,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

let refreshPromise: Promise<string> | null = null;

function clearAuthTokens() {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

async function reissueAccessToken() {
  const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
  if (!refreshToken) {
    throw new Error('no-refresh-token');
  }

  if (!refreshPromise) {
    refreshPromise = reissueClient
      .post<ApiResponse<ReissuePayload>>('/auth/reissue', null, {
        headers: {
          Authorization: `Bearer ${refreshToken}`,
        },
      })
      .then((response) => {
        const newAccessToken = response.data.data?.accessToken;
        if (!newAccessToken) {
          throw new Error('missing-access-token');
        }
        localStorage.setItem(ACCESS_TOKEN_KEY, newAccessToken);
        return newAccessToken;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }

  return refreshPromise;
}

// Request 인터셉터
apiClient.interceptors.request.use(
  (config) => {
    if (config.skipAuth) {
      return config;
    }

    const accessToken = localStorage.getItem(ACCESS_TOKEN_KEY);
    if (accessToken && !config.headers.Authorization) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response 인터셉터
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as RetryableRequestConfig | undefined;

    if (!originalRequest) {
      return Promise.reject(error);
    }

    const status = error.response?.status;
    const requestUrl = originalRequest.url ?? '';
    const isReissueRequest = requestUrl.includes('/auth/reissue');
    const skipAuth = originalRequest.skipAuth;

    if (status === 401 && !skipAuth && !originalRequest._retry && !isReissueRequest) {
      originalRequest._retry = true;
      try {
        const newAccessToken = await reissueAccessToken();
        originalRequest.headers = originalRequest.headers ?? {};
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        return apiClient(originalRequest);
      } catch {
        clearAuthTokens();
        const currentPath = `${window.location.pathname}${window.location.search}${window.location.hash}`;
        const appRelativePath = toAppRelativePath(currentPath);
        const shouldSkipAutoLogin =
          appRelativePath.startsWith('/auth/callback') ||
          appRelativePath.startsWith('/signup');

        if (!shouldSkipAutoLogin) {
          beginSsafyLoginFlow(currentPath);
        }
      }
    }

    if (status === 401) {
      clearAuthTokens();
    } else if (status === 429) {
      console.error('요청 한도 초과: 잠시 후 다시 시도해주세요.');
    }

    return Promise.reject(error);
  }
);
