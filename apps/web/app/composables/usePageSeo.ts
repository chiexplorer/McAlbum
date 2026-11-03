import type { MaybeRefOrGetter } from 'vue'

interface PageSeoOptions {
  title: MaybeRefOrGetter<string>
  description: MaybeRefOrGetter<string>
  image?: MaybeRefOrGetter<string | undefined>
  type?: 'website' | 'article'
}

export function usePageSeo(options: PageSeoOptions): void {
  const route = useRoute()
  const config = useRuntimeConfig()
  const siteUrl = String(config.public.siteUrl).replace(/\/$/, '')
  const canonical = computed(() => `${siteUrl}${route.path}`)
  const title = computed(() => toValue(options.title))
  const description = computed(() => toValue(options.description))
  const image = computed(() => {
    const value = options.image ? toValue(options.image) : undefined
    return value
      ? (value.startsWith('http') ? value : `${siteUrl}${value}`)
      : `${siteUrl}/favicon.svg`
  })

  useHead({ link: [{ rel: 'canonical', href: canonical }] })
  useSeoMeta({
    title,
    description,
    ogTitle: title,
    ogDescription: description,
    ogType: options.type ?? 'website',
    ogUrl: canonical,
    ogImage: image,
    twitterCard: 'summary_large_image',
    twitterTitle: title,
    twitterDescription: description,
    twitterImage: image,
  })
}
