<script setup lang="ts">
import type { Photo, PublicMediaAsset } from '~/schemas/content'

defineProps<{ photo: Photo; asset: PublicMediaAsset }>()
const emit = defineEmits<{ open: [asset: PublicMediaAsset, title: string] }>()

const formatter = new Intl.DateTimeFormat('zh-CN', {
  timeZone: 'Asia/Shanghai',
  month: 'long',
  day: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})
</script>

<template>
  <article class="photo-card">
    <button class="photo-card__media" type="button" :aria-label="`查看大图：${photo.title}`" @click="emit('open', asset, photo.title)">
      <AppMedia :asset="asset" :alt="asset.altText" sizes="(max-width: 720px) 100vw, 50vw" />
    </button>
    <div class="photo-card__body">
      <div>
        <h3><NuxtLink :to="`/photos/${photo.id}`">{{ photo.title }}</NuxtLink></h3>
        <p>{{ photo.description }}</p>
      </div>
      <time :datetime="photo.capturedAt">{{ formatter.format(new Date(photo.capturedAt)) }}</time>
    </div>
  </article>
</template>
