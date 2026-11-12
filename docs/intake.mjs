/** Fail-closed intake for untrusted synthetic text and JSON (V1.4).
 * Mirrors ddlab/intake.py: same checks, same order, same error codes, verified
 * against contracts/intake-vectors.json in both runtimes.
 * Input is decoded, measured, checked and returned as data. It is never
 * evaluated, fetched, stored or treated as an instruction or an authorization.
 * "Tokens" are whitespace-delimited runs, not model tokens.
 */
import {strictJSON} from './strict-json.mjs';

export const DEFAULT_LIMITS = Object.freeze({max_bytes: 524288, max_lines: 20000, max_tokens: 100000, max_depth: 32});

export class IntakeError extends Error {
  constructor(code, detail = '') {
    super(detail ? `${code}: ${detail}` : code);
    this.name = 'IntakeError';
    this.code = code;
  }
}

function limitsFrom(overrides) {
  const limits = {...DEFAULT_LIMITS};
  for (const [key, value] of Object.entries(overrides ?? {})) {
    if (!Object.hasOwn(DEFAULT_LIMITS, key) || !Number.isSafeInteger(value) || value < 0) throw new IntakeError('INVALID_LIMITS', key);
    limits[key] = value;
  }
  return limits;
}

/** Character policy applied to raw text and again to every parsed JSON string. */
export function checkString(text) {
  for (let i = 0; i < text.length; i++) {
    const unit = text.charCodeAt(i);
    if (unit >= 0xD800 && unit <= 0xDBFF) {
      const next = text.charCodeAt(i + 1);
      if (!(next >= 0xDC00 && next <= 0xDFFF)) throw new IntakeError('LONE_SURROGATE');
      i++;
      continue;
    }
    if (unit >= 0xDC00 && unit <= 0xDFFF) throw new IntakeError('LONE_SURROGATE');
    if ((unit < 0x20 && unit !== 0x09 && unit !== 0x0A && unit !== 0x0D) || (unit >= 0x7F && unit <= 0x9F)) {
      throw new IntakeError('CONTROL_CHARACTER', `U+${unit.toString(16).toUpperCase().padStart(4, '0')}`);
    }
    if ((unit >= 0x202A && unit <= 0x202E) || (unit >= 0x2066 && unit <= 0x2069)) {
      throw new IntakeError('BIDI_CONTROL_CHARACTER', `U+${unit.toString(16).toUpperCase()}`);
    }
    if (unit === 0xFEFF) throw new IntakeError('BOM_OR_ZWNBSP');
  }
  if (text.normalize('NFC') !== text) throw new IntakeError('NOT_NFC', 'normalize the source to NFC before import; offsets refer to the given bytes');
}

function countTokens(text) {
  let count = 0;
  for (const part of text.split(/\s+/u)) if (part) count++;
  return count;
}

/** Decode bounded UTF-8 bytes or throw IntakeError. No normalization is applied. */
export function readTextStrict(bytes, limits) {
  if (!(bytes instanceof Uint8Array)) throw new IntakeError('EXPECTED_BYTES');
  const lim = limitsFrom(limits);
  if (bytes.length > lim.max_bytes) throw new IntakeError('TOO_MANY_BYTES');
  let text;
  try {
    text = new TextDecoder('utf-8', {fatal: true, ignoreBOM: true}).decode(bytes);
  } catch {
    throw new IntakeError('INVALID_UTF8');
  }
  checkString(text);
  let lines = 1;
  for (let i = 0; i < text.length; i++) if (text.charCodeAt(i) === 0x0A) lines++;
  if (lines > lim.max_lines) throw new IntakeError('TOO_MANY_LINES');
  if (countTokens(text) > lim.max_tokens) throw new IntakeError('TOO_MANY_TOKENS');
  return text;
}

function walk(value, maxDepth) {
  const pending = [[value, 0]];
  while (pending.length) {
    const [item, depth] = pending.pop();
    if (depth > maxDepth) throw new IntakeError('TOO_DEEP');
    if (typeof item === 'string') checkString(item);
    else if (typeof item === 'number') {
      if (!Number.isFinite(item) || (Number.isInteger(item) && !Number.isSafeInteger(item))) throw new IntakeError('UNSAFE_NUMBER');
    } else if (Array.isArray(item)) {
      for (const child of item) pending.push([child, depth + 1]);
    } else if (item && typeof item === 'object') {
      for (const [key, child] of Object.entries(item)) {
        checkString(key);
        pending.push([child, depth + 1]);
      }
    }
  }
}

/** Bounded, strict UTF-8 JSON: no duplicate keys, unsafe numbers or hidden controls. */
export function parseJsonStrict(bytes, limits) {
  const lim = limitsFrom(limits);
  const text = readTextStrict(bytes, lim);
  if (!/[^\x20\t\n\r]/.test(text)) throw new IntakeError('INVALID_JSON', 'empty document');
  let value;
  try {
    // The pre-parser sees a container at depth d and its children at d+1, like walk() below.
    value = strictJSON(text, {maxBytes: lim.max_bytes, maxDepth: lim.max_depth});
  } catch (error) {
    const message = String(error?.message ?? error);
    if (/Duplicate JSON key/.test(message)) throw new IntakeError('DUPLICATE_KEY');
    if (/depth limit/.test(message) || error instanceof RangeError) throw new IntakeError('TOO_DEEP');
    throw new IntakeError('INVALID_JSON', message.slice(0, 120));
  }
  walk(value, lim.max_depth);
  return value;
}
