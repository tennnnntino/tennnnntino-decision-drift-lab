/** Minimal JSON Schema subset validator (V1.4), mirror of ddlab/schema.py.
 * Unknown keywords make the schema invalid (SchemaError) instead of being ignored.
 * Both runtimes are held to contracts/schema-vectors.json.
 * Contract check for synthetic fixtures only: not a complete JSON Schema
 * implementation and not a security boundary.
 */
const ANNOTATIONS = new Set(['$schema', '$id', 'title', 'description', '$defs', '$comment']);
const SUPPORTED = new Set([...ANNOTATIONS, 'type', 'required', 'properties', 'additionalProperties', 'items', 'enum', 'const',
  'minLength', 'maxLength', 'minItems', 'maxItems', 'minimum', 'maximum', 'pattern', '$ref']);
const TYPES = new Set(['object', 'array', 'string', 'integer', 'number', 'boolean', 'null']);
const MAX_REF_DEPTH = 64;

export class SchemaError extends Error {
  constructor(message) { super(message); this.name = 'SchemaError'; }
}

const isObject = value => value !== null && typeof value === 'object' && !Array.isArray(value);

function isType(value, name) {
  switch (name) {
    case 'object': return isObject(value);
    case 'array': return Array.isArray(value);
    case 'string': return typeof value === 'string';
    case 'boolean': return typeof value === 'boolean';
    case 'null': return value === null;
    case 'number': return typeof value === 'number';
    default: return typeof value === 'number' && Number.isInteger(value);
  }
}

/** JSON equality: booleans never equal numbers; key order is irrelevant. */
export function strictEqual(a, b) {
  if (Array.isArray(a) || Array.isArray(b)) {
    return Array.isArray(a) && Array.isArray(b) && a.length === b.length && a.every((item, i) => strictEqual(item, b[i]));
  }
  if (isObject(a) || isObject(b)) {
    if (!isObject(a) || !isObject(b)) return false;
    const keys = Object.keys(a);
    return keys.length === Object.keys(b).length && keys.every(k => Object.hasOwn(b, k) && strictEqual(a[k], b[k]));
  }
  return a === b;
}

function resolve(root, ref) {
  if (typeof ref !== 'string' || !ref.startsWith('#/$defs/')) throw new SchemaError(`unsupported $ref: ${ref}`);
  const defs = isObject(root.$defs) ? root.$defs : {};
  const name = ref.slice('#/$defs/'.length);
  const target = Object.hasOwn(defs, name) ? defs[name] : undefined;
  if (!isObject(target)) throw new SchemaError(`unresolvable $ref: ${ref}`);
  return target;
}

function pattern(source) {
  if (typeof source !== 'string' || source.length < 2 || !source.startsWith('^') || !source.endsWith('$')) {
    throw new SchemaError('pattern must be a string anchored with ^ and $');
  }
  try { return new RegExp(`^(?:${source.slice(1, -1)})$`, 'u'); }
  catch (error) { throw new SchemaError(`invalid pattern: ${error.message}`); }
}

const codePoints = text => { let n = 0; for (const _ of text) n++; return n; };

function check(value, schema, root, path, errors, depth) {
  if (!isObject(schema)) throw new SchemaError(`schema at ${path || '/'} must be an object`);
  const unknown = Object.keys(schema).filter(k => !SUPPORTED.has(k)).sort();
  if (unknown.length) throw new SchemaError(`unsupported schema keyword(s) at ${path || '/'}: ${unknown.join(', ')}`);
  if (depth > MAX_REF_DEPTH) throw new SchemaError('schema reference depth exceeded');
  const fail = keyword => errors.push({path: path || '/', keyword});

  if (Object.hasOwn(schema, '$ref')) check(value, resolve(root, schema.$ref), root, path, errors, depth + 1);
  if (Object.hasOwn(schema, 'type')) {
    const names = Array.isArray(schema.type) ? schema.type : [schema.type];
    if (!names.length || names.some(n => !TYPES.has(n))) throw new SchemaError(`unsupported type at ${path || '/'}`);
    if (!names.some(n => isType(value, n))) { fail('type'); return; }
  }
  if (Object.hasOwn(schema, 'enum') && !schema.enum.some(option => strictEqual(value, option))) fail('enum');
  if (Object.hasOwn(schema, 'const') && !strictEqual(value, schema.const)) fail('const');
  if (typeof value === 'string') {
    const length = codePoints(value);
    if (Object.hasOwn(schema, 'minLength') && length < schema.minLength) fail('minLength');
    if (Object.hasOwn(schema, 'maxLength') && length > schema.maxLength) fail('maxLength');
    if (Object.hasOwn(schema, 'pattern') && !pattern(schema.pattern).test(value)) fail('pattern');
  }
  if (typeof value === 'number') {
    if (Object.hasOwn(schema, 'minimum') && value < schema.minimum) fail('minimum');
    if (Object.hasOwn(schema, 'maximum') && value > schema.maximum) fail('maximum');
  }
  if (Array.isArray(value)) {
    if (Object.hasOwn(schema, 'minItems') && value.length < schema.minItems) fail('minItems');
    if (Object.hasOwn(schema, 'maxItems') && value.length > schema.maxItems) fail('maxItems');
    if (Object.hasOwn(schema, 'items')) value.forEach((child, i) => check(child, schema.items, root, `${path}/${i}`, errors, depth + 1));
  }
  if (isObject(value)) {
    for (const name of schema.required ?? []) {
      if (!Object.hasOwn(value, name)) errors.push({path: `${path}/${name}`, keyword: 'required'});
    }
    const properties = schema.properties ?? {};
    if (!isObject(properties)) throw new SchemaError('properties must be an object');
    for (const [name, child] of Object.entries(value)) {
      if (Object.hasOwn(properties, name)) check(child, properties[name], root, `${path}/${name}`, errors, depth + 1);
      else if (Object.hasOwn(schema, 'additionalProperties')) {
        const extra = schema.additionalProperties;
        if (extra === false) errors.push({path: `${path}/${name}`, keyword: 'additionalProperties'});
        else if (extra !== true) check(child, extra, root, `${path}/${name}`, errors, depth + 1);
      }
    }
  }
}

/** Returns a sorted list of {path, keyword} violations (empty when valid). */
export function validate(instance, schema, root = schema) {
  const errors = [];
  check(instance, schema, root, '', errors, 0);
  const order = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
  return errors.sort((a, b) => order(a.path, b.path) || order(a.keyword, b.keyword));
}
