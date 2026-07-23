import { API_BASE_URL, API_KEY } from "./config";

export interface VerifyResult {
  valid: boolean;
  namespace: string;
}

/**
 * Generate a new namespace-scoped `oh_ops_` tenant key.
 * Requires the admin/dev key (the key-generation endpoint is admin-gated).
 * The raw key is returned exactly once.
 */
export async function generateKey(namespace: string, label = ""): Promise<string> {
  const res = await fetch(`${API_BASE_URL}/api/v1/keys`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${API_KEY}`,
    },
    body: JSON.stringify({ namespace, label }),
  });
  if (!res.ok) {
    throw new Error(`Key generation failed (${res.status}). Admin key required.`);
  }
  const data = await res.json();
  return data.raw_key as string;
}

/**
 * Verify an API key against the backend, returning the resolved namespace.
 * Throws if the key is invalid or revoked.
 */
export async function verifyKey(rawKey: string): Promise<VerifyResult> {
  const res = await fetch(`${API_BASE_URL}/api/v1/keys/verify`, {
    headers: { Authorization: `Bearer ${rawKey}` },
  });
  if (!res.ok) {
    throw new Error("Invalid or revoked API key.");
  }
  return res.json();
}
