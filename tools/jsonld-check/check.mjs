// Type-check every JSON-LD block on the published pages against the schema.org vocabulary.
//
// Uses schema-dts (Google's TypeScript definitions of schema.org) and the TypeScript compiler,
// so an unknown property, a misspelt type or a wrong value type fails the check.
//   cd tools/jsonld-check && npm ci && node check.mjs
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '../..');
const out = path.join(here, 'generated');
fs.rmSync(out, { recursive: true, force: true });
fs.mkdirSync(out);

const skip = new Set(['reports', 'docs', 'tools', 'node_modules']);
function* htmlFiles(dir) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (e.name.startsWith('.') || e.name.startsWith('_') || skip.has(e.name)) continue;
    const p = path.join(dir, e.name);
    if (e.isDirectory()) yield* htmlFiles(p);
    else if (e.name.endsWith('.html')) yield p;
  }
}

let blocks = 0;
for (const file of htmlFiles(root)) {
  const src = fs.readFileSync(file, 'utf8');
  const re = /<script type="application\/ld\+json">([\s\S]*?)<\/script>/g;
  let m, i = 0;
  while ((m = re.exec(src))) {
    let data;
    const rel = path.relative(root, file);
    try { data = JSON.parse(m[1]); } catch (e) { console.error(`${rel}: invalid JSON: ${e.message}`); process.exit(1); }
    const name = rel.replace(/[^a-z0-9]+/gi, '_') + `_${i++}.ts`;
    const decl = data['@graph']
      ? 'import type { Graph } from "schema-dts";\nexport const data: Graph = '
      : 'import type { Thing, WithContext } from "schema-dts";\nexport const data: WithContext<Thing> = ';
    fs.writeFileSync(path.join(out, name), `// from ${rel}\n${decl}${JSON.stringify(data, null, 1)};\n`);
    blocks++;
  }
}
console.log(`Checking ${blocks} JSON-LD block(s) against schema.org types...`);
try {
  execFileSync(path.join(here, 'node_modules/.bin/tsc'),
    ['--noEmit', '--strict', '--skipLibCheck', '--target', 'es2020', '--moduleResolution', 'node', ...fs.readdirSync(out).map((f) => path.join(out, f))],
    { stdio: 'inherit', cwd: here });
  console.log('All JSON-LD blocks match schema.org.');
} catch {
  console.error('JSON-LD type check failed (see errors above).');
  process.exit(1);
}
