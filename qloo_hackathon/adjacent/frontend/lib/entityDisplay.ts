/** Normalize only presentation whitespace/canonical Unicode; never derive a
 * provider entity name from cohort metadata or evidence prose. */
export function normalizeEntityName(value: string | null | undefined): string | null {
  if (typeof value !== "string") return null;
  const name = value.normalize("NFC").replace(/\s+/gu, " ").trim();
  if (!name) return null;
  // Guard against old/malformed payloads that put construction explanations or
  // identifiers in the identity field. Preserve the source value in the API.
  if (/^urn:(?:entity|tag):/iu.test(name)) return null;
  if (/\b(?:entities returned for this programme|share no qloo tag|grouped because the subtype)\b/iu.test(name)) return null;
  return name;
}
