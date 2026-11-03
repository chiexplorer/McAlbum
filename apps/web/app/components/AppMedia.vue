<script setup lang="ts">
import type { PublicMediaAsset } from '~/schemas/content'

const props = withDefaults(defineProps<{
  asset: PublicMediaAsset
  alt?: string
  eager?: boolean
  sizes?: string
}>(), {
  alt: undefined,
  eager: false,
  sizes: '100vw',
})

const orderedNames = ['w480', 'w960', 'w1440', 'w1920'] as const
const variants = computed(() => orderedNames
  .map(name => props.asset.variants.find(variant => variant.name === name))
  .filter((variant): variant is NonNullable<typeof variant> => Boolean(variant)))

const fallback = computed(() => variants.value.at(-1) ?? props.asset.variants[0])
const srcset = computed(() => variants.value
  .map(variant => `${mediaUrl(variant.storageKey)} ${variant.width}w`)
  .join(', '))
const position = computed(() => `${props.asset.focalPoint.x * 100}% ${props.asset.focalPoint.y * 100}%`)

function mediaUrl(storageKey: string): string {
  return `/${storageKey.replace(/^variants\//, 'media/')}`
}
</script>

<template>
  <img
    v-if="fallback"
    class="app-media"
    :src="mediaUrl(fallback.storageKey)"
    :srcset="srcset"
    :sizes="sizes"
    :alt="alt ?? asset.altText"
    :width="fallback.width"
    :height="fallback.height"
    :loading="eager ? 'eager' : 'lazy'"
    :fetchpriority="eager ? 'high' : 'auto'"
    decoding="async"
    :style="{ objectPosition: position }"
  >
</template>
