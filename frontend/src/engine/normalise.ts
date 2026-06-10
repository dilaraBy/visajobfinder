// Port of pipeline/sponsor_register/normalise.py.
// This file is a PORT and must stay in sync with the Python source of truth.

export const LEGAL_SUFFIXES = new Set([
  "ltd",
  "limited",
  "plc",
  "llp",
  "llc",
  "inc",
  "incorporated",
  "co",
  "company",
  "corp",
  "corporation",
  "cic",
  "gmbh",
  "sa",
  "bv",
]);

export const TRAILING_CONTEXT_SUFFIXES = new Set([
  "uk",
  "group",
  "holdings",
  "holding",
  "international",
]);

const PUNCTUATION_RE = /[^a-z0-9]+/g;

function asciiFold(value: string): string {
  // Python: unicodedata.normalize("NFKD", value).encode("ascii", "ignore")
  // NFKD decomposes accented chars into base + combining marks; encoding to
  // ascii with "ignore" then drops every non-ASCII codepoint (the combining
  // marks plus anything else outside ASCII). We replicate by NFKD-normalising
  // and then removing any codepoint > 0x7F.
  return value
    .normalize("NFKD")
    // eslint-disable-next-line no-control-regex
    .replace(/[^\x00-\x7F]/g, "");
}

function stripSuffixes(tokens: string[]): string[] {
  const filtered = tokens.filter((token) => !LEGAL_SUFFIXES.has(token));
  while (
    filtered.length > 1 &&
    TRAILING_CONTEXT_SUFFIXES.has(filtered[filtered.length - 1])
  ) {
    filtered.pop();
  }
  return filtered;
}

export function normaliseEmployerName(name: string): string {
  if (!name) {
    return "";
  }

  let text = asciiFold(name).toLowerCase();
  text = text.replace(/&/g, " and ");
  text = text.replace(/'/g, "");
  text = text.replace(PUNCTUATION_RE, " ");
  const tokens = stripSuffixes(text.split(/\s+/).filter(Boolean));
  return tokens.join(" ");
}
