<script setup lang="ts">
import type { PublicMediaAsset } from '~/schemas/content'

defineProps<{
  before: PublicMediaAsset
  after: PublicMediaAsset
  beforeLabel: string
  afterLabel: string
}>()
</script>

<template>
  <figure class="image-comparison">
    <div>
      <AppMedia :asset="before" sizes="(max-width: 720px) 100vw, 50vw" />
      <span>{{ beforeLabel }}</span>
    </div>
    <div>
      <AppMedia :asset="after" sizes="(max-width: 720px) 100vw, 50vw" />
      <span>{{ afterLabel }}</span>
    </div>
    <figcaption><slot /></figcaption>
  </figure>
</template>
