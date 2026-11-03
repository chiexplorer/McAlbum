<script setup lang="ts">
import type { CSSProperties } from 'vue'
import type { ResolvedPhoto } from '~/repositories/content-repository'
import { justifiedTargetHeight, justifyPhotoRows } from '~/utils/justified-layout'

const props = defineProps<{ entries: ResolvedPhoto[] }>()
const emit = defineEmits<{ open: [asset: ResolvedPhoto['asset'], title: string] }>()
const grid = useTemplateRef<HTMLDivElement>('grid')
const containerWidth = ref(0)
const gap = 12
let observer: ResizeObserver | undefined

const formatter = new Intl.DateTimeFormat('zh-CN', {
  timeZone: 'Asia/Shanghai',
  year: 'numeric',
  month: 'long',
  day: 'numeric',
})

function aspectRatio(entry: ResolvedPhoto): number {
  const variant = [...entry.asset.variants]
    .filter(item => item.name !== 'placeholder')
    .sort((left, right) => right.width - left.width)[0] ?? entry.asset.variants[0]
  return variant && variant.height > 0 ? variant.width / variant.height : 16 / 9
}

const aspects = computed(() => new Map(
  props.entries.map(entry => [entry.photo.id, aspectRatio(entry)]),
))
const layout = computed(() => new Map(justifyPhotoRows(
  props.entries.map(entry => ({
    id: entry.photo.id,
    aspectRatio: aspects.value.get(entry.photo.id) ?? 16 / 9,
  })),
  containerWidth.value,
  gap,
  justifiedTargetHeight(containerWidth.value),
).map(tile => [tile.id, tile])))

function tileStyle(entry: ResolvedPhoto): CSSProperties {
  const ratio = aspects.value.get(entry.photo.id) ?? 16 / 9
  const tile = layout.value.get(entry.photo.id)
  return {
    '--photo-ratio': String(ratio),
    ...(tile ? { width: `${tile.width}px`, height: `${tile.height}px` } : {}),
  }
}

function measure(): void {
  containerWidth.value = Math.floor(grid.value?.getBoundingClientRect().width ?? 0)
}

onMounted(() => {
  measure()
  if (!grid.value) return
  observer = new ResizeObserver(entries => {
    containerWidth.value = Math.floor(entries[0]?.contentRect.width ?? 0)
  })
  observer.observe(grid.value)
})

onBeforeUnmount(() => observer?.disconnect())
</script>

<template>
  <div ref="grid" class="justified-photo-grid" :class="{ 'is-measured': containerWidth > 0 }">
    <article v-for="entry in entries" :key="entry.photo.id" class="justified-photo" :style="tileStyle(entry)">
      <button type="button" class="justified-photo__media" :aria-label="`查看大图：${entry.photo.title}`" @click="emit('open', entry.asset, entry.photo.title)">
        <AppMedia
          :asset="entry.asset"
          :alt="entry.asset.altText"
          sizes="(max-width: 560px) calc(100vw - 2rem), (max-width: 1300px) 50vw, 42vw"
        />
      </button>
      <div class="justified-photo__caption">
        <NuxtLink :to="`/photos/${entry.photo.id}`">{{ entry.photo.title }}</NuxtLink>
        <time :datetime="entry.photo.capturedAt">{{ formatter.format(new Date(entry.photo.capturedAt)) }}</time>
      </div>
    </article>
  </div>
</template>
