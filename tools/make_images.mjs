// Generate the site's share images (1200x630) and favicons in the site's own colours and fonts.
//
// Needs Playwright with Chromium (npm i playwright && npx playwright install chromium).
// Run from the repository root:  node tools/make_images.mjs   (or name outputs: node tools/make_images.mjs images/og/blog.jpg)
// Edit tools/og-images.json to add a page; use only words that already appear on that page.
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const require = createRequire(process.cwd() + '/');
const { chromium } = require('playwright');
const root = process.cwd();
const cfg = JSON.parse(fs.readFileSync(path.join(root, 'tools/og-images.json'), 'utf8'));

const FONTS = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bodoni+Moda:ital,opsz,wght@0,6..96,500;1,6..96,500&family=Karla:wght@500;600&display=block">';
const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;');
const src = (s) => (/^https?:/.test(s) ? s : 'file://' + path.join(root, s));

const og = (c) => `<!doctype html><html><head><meta charset="utf-8">${FONTS}<style>
*{margin:0;box-sizing:border-box}
body{width:1200px;height:630px;background:#2A1F2C;color:#F4EEF3;font-family:Karla,Arial,sans-serif;display:grid;grid-template-columns:1fr 400px;gap:56px;align-items:center;padding:0 72px;border-left:14px solid #7A1F3D}
.eb{font-size:22px;letter-spacing:.1em;text-transform:uppercase;font-weight:600;color:#C4B8C6;margin-bottom:26px}
h1{font-family:"Bodoni Moda",Georgia,serif;font-weight:500;font-size:${c.headline.length > 30 ? 64 : 78}px;line-height:1.08;text-wrap:balance}
.sub{font-size:26px;color:#C4B8C6;margin-top:28px}
.brand{font-family:"Bodoni Moda",Georgia,serif;font-size:28px;margin-top:44px;color:#F4EEF3}
img{width:400px;height:400px;object-fit:cover;object-position:top;display:block}
img.cover{border-radius:8px;box-shadow:0 24px 60px rgba(0,0,0,.45)}
img.circle{border-radius:50%;border:6px solid #7A1F3D;width:380px;height:380px;margin:auto}
</style></head><body><div><p class="eb">${esc(c.eyebrow)}</p><h1>${esc(c.headline)}</h1><p class="sub">${esc(c.sub)}</p><p class="brand">kayjoyflowers.online</p></div>
<img class="${c.shape}" src="${src(c.image)}" alt=""></body></html>`;

const icon = (size) => `<!doctype html><html><head><meta charset="utf-8">${FONTS}<style>
*{margin:0}body{width:${size}px;height:${size}px;background:#7A1F3D;display:grid;place-items:center}
span{font-family:"Bodoni Moda",Georgia,serif;font-weight:500;color:#F4EEF3;font-size:${Math.round(size * 0.78)}px;line-height:1;transform:translateY(-${Math.round(size * 0.03)}px)}
</style></head><body><span>K</span></body></html>`;

const browser = await chromium.launch();
async function render(html, w, h, out, type) {
  const p = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
  const tmp = path.join(root, '.og-tmp.html');
  fs.writeFileSync(tmp, html);
  await p.goto('file://' + tmp, { waitUntil: 'networkidle' });
  await p.evaluate(() => document.fonts.ready);
  await p.screenshot({ path: out, type, ...(type === 'jpeg' ? { quality: 84 } : { omitBackground: true }) });
  fs.unlinkSync(tmp);
  await p.close();
  console.log('wrote', out);
}
const only = process.argv.slice(2);   // optional: render just these outputs, e.g. images/og/blog.jpg
for (const c of cfg.images) if (!only.length || only.includes(c.out)) await render(og(c), 1200, 630, path.join(root, c.out), 'jpeg');
if (!only.length) for (const [size, out] of [[32, 'images/favicon-32.png'], [48, 'images/favicon-48.png'], [192, 'images/icon-192.png'], [180, 'apple-touch-icon.png']]) {
  await render(icon(size), size, size, path.join(root, out), 'png');
}
await browser.close();
