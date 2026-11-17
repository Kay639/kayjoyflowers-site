// Measure pages with Lighthouse (mobile, simulated throttling) and keep the median of N runs.
//
// Setup (once, outside the repo or in a temp folder):  npm i lighthouse@12
// Run:  node tools/lighthouse_runs.mjs --base https://kayjoyflowers.online --runs 3 --out lh.json [paths...]
// Env:  CHROME_PATH=/path/to/chrome (optional), HTTPS_PROXY is passed to Chrome if set.
//
// Lighthouse scores vary between runs; the median of 3 is the figure reported.
import { createRequire } from 'node:module';
import fs from 'node:fs';

const require = createRequire(process.cwd() + '/');
const lighthouse = (await import(require.resolve('lighthouse'))).default;
const chromeLauncher = await import(require.resolve('chrome-launcher'));

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args.splice(i, 2)[1] : d; };
const base = opt('--base', 'https://kayjoyflowers.online').replace(/\/$/, '');
const runs = Number(opt('--runs', '3'));
const out = opt('--out', 'lighthouse.json');
const paths = args.length ? args : ['/', '/fearlessly-unfuckwithable.html', '/genius-insight.html',
  '/about.html', '/library.html', '/privacy.html'];

const flags = ['--headless=new', '--no-sandbox', '--disable-gpu'];
if (process.env.HTTPS_PROXY) flags.push(`--proxy-server=${process.env.HTTPS_PROXY}`);
const median = (a) => { const s = [...a].sort((x, y) => x - y); return s[Math.floor(s.length / 2)]; };

const result = { base, runs, date: new Date().toISOString(), lighthouse: null, pages: {} };
for (const p of paths) {
  const samples = [];
  for (let i = 0; i < runs; i++) {
    const chrome = await chromeLauncher.launch({ chromeFlags: flags, chromePath: process.env.CHROME_PATH });
    try {
      const r = await lighthouse(base + p, {
        port: chrome.port, output: 'json', logLevel: 'error',
        onlyCategories: ['performance', 'accessibility', 'best-practices', 'seo'],
      });
      const l = r.lhr;
      result.lighthouse = l.lighthouseVersion;
      const a = l.audits;
      samples.push({
        performance: Math.round(l.categories.performance.score * 100),
        accessibility: Math.round(l.categories.accessibility.score * 100),
        bestPractices: Math.round(l.categories['best-practices'].score * 100),
        seo: Math.round(l.categories.seo.score * 100),
        lcp: a['largest-contentful-paint'].numericValue,
        fcp: a['first-contentful-paint'].numericValue,
        cls: a['cumulative-layout-shift'].numericValue,
        tbt: a['total-blocking-time'].numericValue,
        bytes: a['total-byte-weight'].numericValue,
        failed: Object.values(a).filter((x) => x.score !== null && x.score < 0.9 &&
          ['binary', 'numeric', 'metricSavings'].includes(x.scoreDisplayMode) || (x.score === 0 && x.scoreDisplayMode === 'binary'))
          .map((x) => x.id),
      });
    } catch (e) {
      console.error(p, String(e).slice(0, 200));
    } finally {
      await chrome.kill();
    }
  }
  if (!samples.length) continue;
  const m = {};
  for (const k of ['performance', 'accessibility', 'bestPractices', 'seo', 'lcp', 'fcp', 'cls', 'tbt', 'bytes']) {
    m[k] = median(samples.map((s) => s[k]));
  }
  m.failedAudits = [...new Set(samples.flatMap((s) => s.failed))].sort();
  m.samples = samples.map(({ failed, ...s }) => s);
  result.pages[p] = m;
  console.log(`${p.padEnd(34)} perf ${m.performance}  a11y ${m.accessibility}  bp ${m.bestPractices}  seo ${m.seo}  LCP ${(m.lcp / 1000).toFixed(2)}s  CLS ${m.cls.toFixed(3)}  TBT ${Math.round(m.tbt)}ms`);
}
fs.writeFileSync(out, JSON.stringify(result, null, 1));
console.log(`Wrote ${out}`);
