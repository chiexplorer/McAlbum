<script setup lang="ts">
import type { PublicMediaAsset, Story } from '~/schemas/content'

const props = defineProps<{
  story: Story
  assetsById: Map<string, PublicMediaAsset>
}>()

function assetFor(id: string): PublicMediaAsset {
  const asset = props.assetsById.get(id)
  if (!asset) throw new Error(`专题引用的媒体 ${id} 不存在`)
  return asset
}
</script>

<template>
  <div class="story-sections">
    <template v-for="section in story.sections" :key="section.id">
      <p v-if="section.type === 'text'" class="story-prose">{{ section.body }}</p>

      <figure v-else-if="section.type === 'wide-image'" class="story-wide">
        <AppMedia :asset="assetFor(section.assetId)" sizes="100vw" />
        <figcaption>{{ section.caption }}</figcaption>
      </figure>

      <figure v-else-if="section.type === 'image-grid'" class="story-image-grid">
        <AppMedia
          v-for="assetId in section.assetIds"
          :key="assetId"
          :asset="assetFor(assetId)"
          sizes="(max-width: 680px) 100vw, 33vw"
        />
        <figcaption v-if="section.caption">{{ section.caption }}</figcaption>
      </figure>

      <section v-else-if="section.type === 'text-with-image'" class="story-split" :class="`story-split--${section.imagePosition}`">
        <AppMedia :asset="assetFor(section.assetId)" sizes="(max-width: 760px) 100vw, 58vw" />
        <p>{{ section.body }}</p>
      </section>

      <blockquote v-else-if="section.type === 'player-quote'" class="story-quote">
        <p>{{ section.quote }}</p>
        <cite>服务器居民</cite>
      </blockquote>

    </template>
  </div>
</template>
