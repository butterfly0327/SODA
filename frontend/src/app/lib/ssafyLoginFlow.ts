import { buildSsafyAuthorizeUrl } from "./ssafyOAuth";
import {
  buildAppPath,
  getAuthStorageKeys,
  rememberLoginRedirectTarget,
} from "./authNavigation";

const SSAFY_CONSENT_KEY = `${getAuthStorageKeys().storage}::ssafy-consent-v1`;
const SSAFY_LOGIN_IN_FLIGHT_KEY = `${getAuthStorageKeys().storage}::ssafy-login-in-flight-v1`;
const SSAFY_SUPPRESS_AUTO_LOGIN_ONCE_KEY = `${getAuthStorageKeys().storage}::ssafy-suppress-auto-login-once-v1`;

export function hasSsafyConsentGranted() {
  if (typeof window === "undefined") {
    return true;
  }

  return window.localStorage.getItem(SSAFY_CONSENT_KEY) === "1";
}

export function markSsafyConsentGranted() {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(SSAFY_CONSENT_KEY, "1");
}

function setLoginInFlight() {
  if (typeof window === "undefined") {
    return;
  }

  window.sessionStorage.setItem(SSAFY_LOGIN_IN_FLIGHT_KEY, "1");
}

function isLoginInFlight() {
  if (typeof window === "undefined") {
    return false;
  }

  return window.sessionStorage.getItem(SSAFY_LOGIN_IN_FLIGHT_KEY) === "1";
}

export function clearSsafyLoginInFlight() {
  if (typeof window === "undefined") {
    return;
  }

  window.sessionStorage.removeItem(SSAFY_LOGIN_IN_FLIGHT_KEY);
}

export function clearSsafyConsent() {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(SSAFY_CONSENT_KEY);
}

export function suppressSsafyAutoLoginOnce() {
  if (typeof window === "undefined") {
    return;
  }

  window.sessionStorage.setItem(SSAFY_SUPPRESS_AUTO_LOGIN_ONCE_KEY, "1");
}

function consumeSsafyAutoLoginSuppression() {
  if (typeof window === "undefined") {
    return false;
  }

  const shouldSuppress =
    window.sessionStorage.getItem(SSAFY_SUPPRESS_AUTO_LOGIN_ONCE_KEY) === "1";
  if (shouldSuppress) {
    window.sessionStorage.removeItem(SSAFY_SUPPRESS_AUTO_LOGIN_ONCE_KEY);
  }

  return shouldSuppress;
}

export function beginSsafyLoginFlow(nextPath?: string) {
  if (consumeSsafyAutoLoginSuppression()) {
    window.location.href = buildAppPath("/");
    return;
  }

  if (nextPath) {
    rememberLoginRedirectTarget(nextPath);
  }

  if (hasSsafyConsentGranted()) {
    if (isLoginInFlight()) {
      return;
    }

    setLoginInFlight();
    window.location.href = buildSsafyAuthorizeUrl();
    return;
  }

  window.location.href = buildAppPath("/signup");
}
