/** Strict browser JSON parser: rejects duplicate (including escaped) object keys.
 * Lexical preflight only; the platform JSON.parse remains the value parser.
 * 64-depth/512 KiB guards apply before parsing. This is not a full schema validator.
 */
export function strictJSON(text, {maxBytes = 524288, maxDepth = 64} = {}) {
  if (typeof text !== 'string') throw new Error('Expected JSON text');
  if (new TextEncoder().encode(text).length > maxBytes) throw new Error('Input exceeds byte limit');
  let p = 0;
  const fail = message => {throw new Error(`${message} at character ${p}`);};
  const ws = () => {while (p < text.length && /[\x20\t\n\r]/.test(text[p])) p++;};
  function stringToken(){
    if (text[p] !== '"') fail('Expected JSON string');
    const begin = p++;
    while (p < text.length){
      const ch = text[p++];
      if (ch === '"') return JSON.parse(text.slice(begin, p));
      if (ch === '\\') {
        if (p >= text.length) fail('Invalid escape');
        const esc = text[p++];
        if ('"\\/bfnrt'.includes(esc)) continue;
        if (esc === 'u'){
          if (!/^[0-9a-fA-F]{4}$/.test(text.slice(p,p+4))) fail('Invalid Unicode escape');
          p+=4;continue;
        }
        fail('Invalid escape');
      }
      if (ch.charCodeAt(0) < 32) fail('Invalid control character');
    }
    fail('Unterminated JSON string');
  }
  function value(depth){
    if (depth > maxDepth) fail('JSON nesting exceeds depth limit');
    ws();
    const c=text[p];
    if (c==='"'){stringToken();return;}
    if (c==='{'){
      p++;ws();const seen=new Set();
      if (text[p]==='}'){p++;return;}
      for(;;){
        ws();const key=stringToken();
        if(seen.has(key)) fail(`Duplicate JSON key: ${key.slice(0,80)}`);
        seen.add(key);ws();if(text[p++]!==':')fail('Expected colon');
        value(depth+1);ws();
        if(text[p]==='}'){p++;return;}
        if(text[p++]!==',')fail('Expected object comma');
      }
    }
    if (c==='['){
      p++;ws();if(text[p]===']'){p++;return;}
      for(;;){value(depth+1);ws();if(text[p]===']'){p++;return;}
        if(text[p++]!==',')fail('Expected array comma');}
    }
    if(c==='t'&&text.slice(p,p+4)==='true'){p+=4;return;}
    if(c==='f'&&text.slice(p,p+5)==='false'){p+=5;return;}
    if(c==='n'&&text.slice(p,p+4)==='null'){p+=4;return;}
    const num=/^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/.exec(text.slice(p));
    if(num){p+=num[0].length;return;}
    fail('Invalid JSON value');
  }
  ws();value(0);ws();if(p!==text.length)fail('Trailing data');
  const parsed=JSON.parse(text);
  // JS JSON.parse accepts unpaired surrogates in escapes; reports are structural only.
  return parsed;
}
