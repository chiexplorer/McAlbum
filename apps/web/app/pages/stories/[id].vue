<script setup lang="ts">
const route = useRoute()
const id = (Array.isArray(route.params.id) ? route.params.id[0] : route.params.id) ?? ''
const { content, loading, unavailable } = usePublicStory(id)

const coverAsset = computed(() => content.value?.assetsById.get(content.value.story.coverAssetId))
const ogVariant = computed(() => coverAsset.value?.variants.find(variant => variant.name === 'w1920')
  ?? coverAsset.value?.variants.at(-1))

usePageSeo({
  title: computed(() => content.value ? `${content.value.story.title} · McAlbum` : '历史专题 · McAlbum'),
  description: computed(() => content.value?.story.summary ?? '阅读服务器已经发布的历史作品集。'),
  image: computed(() => ogVariant.value ? `/${ogVariant.value.storageKey.replace(/^variants\//, 'media/')}` : undefined),
  type: 'article',
})
</script>

<template>
  <main v-if="content && coverAsset" id="main-content" class="story-page">
    <header class="story-hero">
      <AppMedia :asset="coverAsset" eager sizes="100vw" />
      <div class="story-hero__overlay page-container">
        <p class="section-kicker">历史专题</p>
        <h1>{{ content.story.title }}</h1>
        <p>{{ content.story.summary }}</p>
      </div>
    </header>
    <StorySections :story="content.story" :assets-by-id="content.assetsById" />
    <div class="detail-actions page-container"><ShareButton :title="content.story.title" :text="content.story.summary" /></div>
  </main>
  <main v-else id="main-content" class="listing-page page-container">
    <EmptyState
      :title="loading ? '正在读取作品集' : '这篇作品集尚未公开'"
      :description="unavailable ? '公开 API 暂时不可用，请稍后刷新页面。' : '作品集可能尚未发布，或已经归档。'"
    />
  </main>
</template>
