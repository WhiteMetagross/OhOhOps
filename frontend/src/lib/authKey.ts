import { API_KEY } from "./config";

/**
 * Tenant API-key storage for the SaaS model.
 *
 * In cloud mode there is no login: a namespace-scoped `oh_ops_` key (generated
 * and verified on the onboarding page) is the tenant boundary. We persist the
 * verified key in localStorage and use it to authenticate every dashboard API
 * call. When no tenant key is present we fall back to the build-time dev/admin
 * key (used by local mode and during development).
 */

const STORAGE_KEY = "nx_saas_key";

export function getStoredSaasKey(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(STORAGE_KEY);
}

export function setStoredSaasKey(key: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, key);
}

export function clearStoredSaasKey(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(STORAGE_KEY);
}

/** The bearer token to authenticate dashboard API calls with. */
export function getAuthKey(): string {
  return getStoredSaasKey() || API_KEY;
}
