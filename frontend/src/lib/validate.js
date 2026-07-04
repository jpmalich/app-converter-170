// Iter 79j.49 — Soft input validators.
//
// Policy: warn, don't block. Every validator treats EMPTY as valid —
// the field only becomes invalid when the user actually typed
// something that fails the format. Requiredness is enforced at the
// action that needs the value (e.g. QuoteModal disables Send on a
// malformed recipient email), not here.

// Basic something@something.tld shape. Not RFC-perfect on purpose —
// the goal is to catch typos ("gmial.con") without rejecting valid
// unusual addresses.
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

export function isValidEmail(value) {
  const v = (value ?? "").trim();
  if (!v) return true;
  return EMAIL_RE.test(v);
}

// Strip non-digits; valid if exactly 10 digits, or 11 with a leading 1
// (the US country code). Extensions ("x1234") make the raw string
// longer — those should stay untouched and NOT be flagged, so we only
// warn on cleanly-numeric strings that don't hit 10/11.
export function isValidPhone(value) {
  const raw = (value ?? "").trim();
  if (!raw) return true;
  const digits = raw.replace(/\D/g, "");
  // Anything with an 'x'/'ext' or other alpha character is treated
  // as intentionally formatted (extension, international, etc.) and
  // left alone.
  if (/[a-wyz]/i.test(raw)) return true;
  if (digits.length === 10) return true;
  if (digits.length === 11 && digits.startsWith("1")) return true;
  return false;
}

export function isValidZip(value) {
  const v = (value ?? "").trim();
  if (!v) return true;
  return /^\d{5}(-\d{4})?$/.test(v);
}

// Return "(AAA) BBB-CCCC" when the input is a clean 10-digit US number
// (or 11 digits with a leading 1). Any other shape — extensions,
// international prefixes, in-progress typing — is returned untouched
// so we never mangle a value the contractor deliberately entered.
export function formatPhoneUS(value) {
  const raw = (value ?? "").toString();
  if (!raw.trim()) return raw;
  if (/[a-wyz]/i.test(raw)) return raw;   // 'x1234' / 'ext.' — leave alone
  const digits = raw.replace(/\D/g, "");
  let d = digits;
  if (d.length === 11 && d.startsWith("1")) d = d.slice(1);
  if (d.length !== 10) return raw;
  return `(${d.slice(0, 3)}) ${d.slice(3, 6)}-${d.slice(6)}`;
}
