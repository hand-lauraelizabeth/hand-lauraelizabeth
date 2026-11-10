/** Reject ambiguous JSON member names before native JSON.parse discards them.
 * Browser-local, dependency-free; uses decoded keys so escaped aliases collide.
 * RFC 8259 section 4 warns that duplicate-key interpretation is unpredictable.
 */
export function assertUniqueJSONKeys(source) {
  if (typeof source !== 'string') throw new Error('Invalid JSON text');
  let pos = 0;
  const fail = () => { throw new Error('Invalid JSON syntax'); };
  const ws = () => { while (pos < source.length && /[ \t\r\n]/.test(source[pos])) pos++; };
  const string = () => {
    if (source[pos] !== '"') fail();
    const start = pos++;
    let closed = false;
    while (pos < source.length) {
      const c = source[pos++];
      if (c === '\\') {
        if (pos >= source.length) fail();
        pos++; // JSON.parse validates the escaped character or \uXXXX sequence.
      } else if (c === '"') { closed = true; break; }
      else if (c.charCodeAt(0) < 32) fail();
    }
    if (!closed) fail();
    try { return JSON.parse(source.slice(start, pos)); }
    catch { fail(); }
  };
  const value = (depth) => {
    if (depth > 32) throw new Error('JSON nesting limit exceeded');
    ws();
    const c = source[pos];
    if (c === '{') {
      pos++; ws();
      const seen = new Set();
      if (source[pos] === '}') { pos++; return; }
      while (true) {
        const key = string();
        if (seen.has(key)) throw new Error('Duplicate JSON object key; nothing imported');
        seen.add(key);
        ws(); if (source[pos++] !== ':') fail();
        value(depth + 1); ws();
        if (source[pos] === '}') { pos++; return; }
        if (source[pos++] !== ',') fail();
        ws();
      }
    }
    if (c === '[') {
      pos++; ws();
      if (source[pos] === ']') { pos++; return; }
      while (true) {
        value(depth + 1); ws();
        if (source[pos] === ']') { pos++; return; }
        if (source[pos++] !== ',') fail();
      }
    }
    if (c === '"') { string(); return; }
    for (const token of ['true', 'false', 'null']) {
      if (source.startsWith(token, pos)) { pos += token.length; return; }
    }
    const match = /^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/.exec(source.slice(pos));
    if (match) { pos += match[0].length; return; }
    fail();
  };
  value(0); ws();
  if (pos !== source.length) fail();
}
