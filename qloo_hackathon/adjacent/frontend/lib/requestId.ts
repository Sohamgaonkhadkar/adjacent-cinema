/**
 * Deterministic request identifiers for the append-only write endpoints.
 *
 * Every write in this application (`/experiments`, observations, evaluations,
 * sponsor drafts, source reviews, outreach, discovery) is idempotent on
 * `request_id`: the backend stores the first record under that id and returns
 * it again — with `duplicate: true` — on a repeat. That is the mechanism that
 * makes a retry after a timeout safe.
 *
 * A timestamp defeats it: retrying the *same* content after a network failure
 * produced a second record, so a creator who clicked twice (or whose first
 * request timed out but still landed) ended up with two "one-off" observations
 * that looked like two separate measurements. Deriving the id from the content
 * instead means the retry reuses the original id and the backend deduplicates
 * it, exactly as intended.
 *
 * The hash is a 64-bit FNV-1a rendered in base 36. It is not a security
 * primitive — it only has to be stable for identical input and spread out for
 * different input.
 */

function canonicalise(value: unknown): string {
  if (value === null || typeof value !== "object") return JSON.stringify(value ?? null);
  if (Array.isArray(value)) return `[${value.map(canonicalise).join(",")}]`;
  const entries = Object.entries(value as Record<string, unknown>)
    .filter(([, entry]) => entry !== undefined)
    .sort(([left], [right]) => (left < right ? -1 : left > right ? 1 : 0));
  return `{${entries.map(([key, entry]) => `${JSON.stringify(key)}:${canonicalise(entry)}`).join(",")}}`;
}

function fnv1a64(input: string): string {
  // Two 32-bit lanes so the digest fits JS integers without BigInt.
  let high = 0xcbf2;
  let low = 0x9ce4cbfb;
  for (let index = 0; index < input.length; index += 1) {
    const code = input.charCodeAt(index);
    low ^= code & 0xff;
    low = Math.imul(low, 0x01000193) >>> 0;
    high ^= (code >>> 8) ^ (low & 0x07);
    high = Math.imul(high, 0x01000193) >>> 0;
  }
  return `${high.toString(36)}${low.toString(36)}`;
}

/**
 * Build a stable request id from a prefix and the submitted content.
 *
 * Prefixes stay human-readable in the stored record (`obs-…`, `spd-draft-…`),
 * the digest keeps the whole id inside the backend's 8–120 character contract.
 */
export function stableRequestId(prefix: string, payload: unknown): string {
  return `${prefix}-${fnv1a64(canonicalise(payload))}`;
}
