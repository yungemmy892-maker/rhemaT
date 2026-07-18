import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

// The access token lives in memory ONLY — never localStorage, never a
// plain (non-httpOnly) cookie. It's short-lived (15 min) and is re-minted
// from the httpOnly refresh cookie via /auth/refresh/ on every full page
// load (see AuthContext's loadSession). This closes audit finding L1: the
// cost is one extra request on load, in exchange for neither token ever
// being readable at rest by any JS running on the page, including an XSS
// payload if one is ever introduced.
let accessToken: string | null = null;

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null) {
  accessToken = token;
}

// Companion CSRF cookie set alongside the httpOnly refresh cookie — see
// backend/auth_api/cookies.py. Deliberately NOT httpOnly so this can read
// it and echo it back in the X-CSRF-Token header.
const CSRF_COOKIE_NAME = "verseid_csrf";

function readCsrfCookie(): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${CSRF_COOKIE_NAME}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
  // Required so the browser attaches the httpOnly refresh cookie (and CSRF
  // cookie) on requests to the API, and stores cookies set on responses.
  withCredentials: true,
});

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  // Only /auth/refresh/ and /auth/logout/ actually check this header, but
  // attaching it whenever the cookie exists is harmless on every other
  // request and keeps this interceptor simple.
  const csrfToken = readCsrfCookie();
  if (csrfToken) {
    config.headers["X-CSRF-Token"] = csrfToken;
  }
  return config;
});

// --- Single-flight refresh: if multiple requests 401 at once, only refresh once. ---
let refreshPromise: Promise<string | null> | null = null;

/**
 * Exchanges the httpOnly refresh cookie for a fresh access token. Used both
 * by the 401 retry flow below and by AuthContext on initial app load, since
 * the in-memory access token doesn't survive a page reload.
 */
export async function refreshAccessToken(): Promise<string | null> {
  if (!refreshPromise) {
    refreshPromise = axios
      .post(
        `${API_BASE_URL}/auth/refresh/`,
        {},
        { withCredentials: true, headers: { "X-CSRF-Token": readCsrfCookie() ?? "" } },
      )
      .then((res) => {
        const { access_token } = res.data;
        setAccessToken(access_token);
        return access_token as string;
      })
      .catch(() => {
        setAccessToken(null);
        return null;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as
      | (InternalAxiosRequestConfig & { _retry?: boolean })
      | undefined;

    const isAuthEndpoint = originalRequest?.url?.includes("/auth/");

    if (
      error.response?.status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      !isAuthEndpoint
    ) {
      originalRequest._retry = true;
      const newToken = await refreshAccessToken();
      if (newToken) {
        originalRequest.headers = originalRequest.headers ?? {};
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return api(originalRequest);
      }
      // Refresh failed — let the app's auth state react (e.g. redirect to /auth)
      window.dispatchEvent(new CustomEvent("verseid:auth-expired"));
    }

    return Promise.reject(normalizeApiError(error));
  },
);

export interface ApiError {
  status: number;
  message: string;
}

export function normalizeApiError(error: AxiosError): ApiError {
  const data = error.response?.data as { error?: { code: number; message: string } } | undefined;
  if (data?.error) {
    return { status: data.error.code, message: data.error.message };
  }
  if (error.message === "Network Error" || !error.response) {
    return { status: 0, message: "Can't reach the server. Check your connection and try again." };
  }
  return { status: error.response.status, message: "Something went wrong. Please try again." };
}