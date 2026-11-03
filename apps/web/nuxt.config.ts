import { fileURLToPath } from 'node:url'

export default defineNuxtConfig({
  compatibilityDate: '2026-10-01',
  devtools: { enabled: true },
  modules: ['@nuxt/image'],
  css: ['~/assets/css/main.css'],
  alias: {
    '@mcalbum/content': fileURLToPath(new URL('../../content', import.meta.url)),
  },
  runtimeConfig: {
    public: {
      siteUrl: process.env.NUXT_PUBLIC_SITE_URL || 'http://localhost:3000',
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000/api',
    },
  },
  app: {
    head: {
      htmlAttrs: { lang: 'zh-CN' },
      link: [{ rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' }],
      meta: [
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'theme-color', content: '#f3f0e8' },
        { property: 'og:site_name', content: 'McAlbum' },
        { property: 'og:locale', content: 'zh_CN' },
      ],
    },
  },
  image: {
    format: ['avif', 'webp'],
    screens: {
      sm: 640,
      md: 768,
      lg: 1024,
      xl: 1280,
      xxl: 1536,
    },
  },
  nitro: {
    publicAssets: [
      {
        dir: fileURLToPath(new URL('../../storage/variants', import.meta.url)),
        baseURL: '/media',
        maxAge: 60 * 60 * 24 * 30,
      },
    ],
    prerender: {
      crawlLinks: true,
    },
  },
  typescript: {
    strict: true,
    typeCheck: true,
    tsConfig: {
      compilerOptions: {
        resolveJsonModule: true,
      },
    },
  },
})
