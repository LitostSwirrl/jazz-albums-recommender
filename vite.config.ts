import { copyFileSync, mkdirSync, readdirSync } from 'node:fs'
import path from 'node:path'
import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { siteConfig as jazzConfig } from './src/sites/jazz/config'
import { siteConfig as funkConfig } from './src/sites/funk/config'
import type { SiteConfig } from './src/types/site'

const site = process.env.VITE_SITE ?? 'jazz'

const configs: Record<string, SiteConfig> = { jazz: jazzConfig, funk: funkConfig }
const activeConfig = configs[site]
if (!activeConfig) throw new Error(`unknown VITE_SITE: ${site}`)

function siteHtml(config: SiteConfig): Plugin {
  const analytics = config.analyticsWebsiteId
    ? `<script defer src="https://cloud.umami.is/script.js" data-website-id="${config.analyticsWebsiteId}"></script>`
    : ''
  const tokens: Record<string, string> = {
    '%SITE_NAME%': config.name,
    '%SITE_TAGLINE%': config.tagline,
    '%SITE_DESCRIPTION%': config.seoDescription,
    '%SITE_URL%': config.url,
    '%SITE_ANALYTICS%': analytics,
  }
  return {
    name: 'site-html',
    transformIndexHtml: html =>
      Object.entries(tokens).reduce((h, [k, v]) => h.replaceAll(k, () => v), html),
  }
}

function sharedPublic(): Plugin {
  return {
    name: 'shared-public',
    closeBundle() {
      mkdirSync('dist', { recursive: true })
      for (const f of readdirSync('public-shared'))
        copyFileSync(`public-shared/${f}`, `dist/${f}`)
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss(), siteHtml(activeConfig), sharedPublic()],
  base: '/',
  publicDir: `src/sites/${site}/public`,
  resolve: {
    alias: { '@site': path.resolve(__dirname, `src/sites/${site}`) },
  },
  optimizeDeps: {
    include: ['dagre'],
  },
  build: {
    commonjsOptions: {
      include: [/node_modules/],
      transformMixedEsModules: true,
    },
    rollupOptions: {
      output: {
        // Stable vendor chunks so content/data updates don't invalidate library caches.
        // graph-vendor is only pulled in by the lazy InfluenceGraph route.
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom', 'react-helmet-async'],
          'graph-vendor': ['@xyflow/react', 'dagre'],
        },
      },
    },
  },
})
