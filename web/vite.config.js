import { execSync } from 'node:child_process'
import { createReadStream, existsSync, readdirSync, statSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

// D128: vendored LLM weights/ORT runtime are served RAW, bypassing Vite's
// transform pipeline — requesting the ORT .mjs with ?import crashes the
// rolldown transform (fast 500) and wedges every subsequent request.
// A raw stream is also the only sane way to serve 1.6 GB onnx files.
const rawModelsPlugin = {
  name: 'raw-models-static',
  apply: 'serve', // D128: dev-server middleware only — never touches builds
  configureServer(server) {
    // web/models/ (NOT public/) — huge vendored assets stay out of the
    // build pipeline; `vite build` never sees them (they wedged rolldown
    // at multi-GB RSS), and deploys copy models/ into dist/ afterwards.
    const root = resolve('models')
    server.middlewares.use((req, res, next) => {
      const url = req.url || ''
      if (!url.startsWith('/models/')) return next()
      const rel = decodeURIComponent(url.split('?')[0]).replace(/^\/models\//, '')
      const file = join(root, 'models', rel)
      if (!file.startsWith(join(root, 'models')) || !existsSync(file) || !statSync(file).isFile()) {
        return next()
      }
      const ct = file.endsWith('.wasm') ? 'application/wasm'
        : (file.endsWith('.mjs') || file.endsWith('.js')) ? 'text/javascript'
        : file.endsWith('.json') ? 'application/json' : 'application/octet-stream'
      res.setHeader('Content-Type', ct)
      res.setHeader('Cache-Control', 'public, max-age=31536000, immutable')
      createReadStream(file).pipe(res)
    })
  },
}

// Last git commit timestamp — shown on the home page as "Page updated".
// Falls back to (and takes the max of) the newest source mtime so
// uncommitted working-tree changes are reflected honestly.
function lastUpdated() {
  let commit = ''
  try { commit = execSync('git log -1 --format=%cI').toString().trim() } catch { /* no git */ }
  let newest = 0
  const walk = (dir) => {
    for (const e of readdirSync(dir, { withFileTypes: true })) {
      const p = join(dir, e.name)
      if (e.isDirectory()) walk(p)
      else if (/\.(svelte|js|json|css)$/.test(e.name)) {
        const m = statSync(p).mtimeMs
        if (m > newest) newest = m
      }
    }
  }
  try { walk(join(process.cwd(), 'src')) } catch { /* no src */ }
  const fromMtime = newest ? new Date(newest).toISOString() : ''
  return [commit, fromMtime].sort().pop() || ''
}

// https://vite.dev/config/
export default defineConfig({
  base: './',              // relative asset paths — dist works under any subfolder
  plugins: [rawModelsPlugin, svelte(), tailwindcss()],
  define: {
    __PAGE_UPDATED__: JSON.stringify(lastUpdated()),
  },
  optimizeDeps: {
    // D128: cold dep-bundling wedged Vite v8 at multi-GB RSS mid-mermaid/igv;
    // both are dynamically imported, so dev serves their ESM unoptimized
    // (prod build is unaffected). onnxruntime-web likewise excluded — its
    // dist variants are pure dead weight to the bundler.
    //
    // 2026-09-22 root cause found: ALL "vite wedges" of this era — dev serve,
    // warmup, AND `vite build`, on vite 7 and 8 alike — were Tailwind v4's
    // oxide scanner ingesting the un-gitignored 2.2 GB vendored models/ tree
    // (now negated in src/app.css + .gitignore). These exclusions were kept
    // as-is; revisit if dep bundling should ever be revisited.
    // D128 history: mermaid was once excluded (dep-bundling memory wedge);
    // root cause was later fixed (Tailwind oxide scanning vendored models/).
    // 2026-10-07: mermaid REMOVED from exclude — excluding it made every
    // CJS dep inside mermaid (dayjs, @braintree/sanitize-url, ...) resolve
    // to raw UMD in dev, killing diagram rendering with
    // "doesn't provide an export named" errors.
    exclude: ['maplibre-gl', '@huggingface/transformers', 'onnxruntime-web', 'igv']
  },
  server: {
    // Pre-transform the app graph at startup so the first remote page load
    // hits warm cache (completes in ~seconds on 8.3.0 post-tailwind-fix).
    warmup: {
      clientFiles: ['./index.html', './src/**/*.{js,svelte}', './src/lib/**/*.{js,svelte}']
    }
  }
})
