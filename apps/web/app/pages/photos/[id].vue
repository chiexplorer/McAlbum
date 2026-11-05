<script setup lang="ts">
const route = useRoute()
const id = (Array.isArray(route.params.id) ? route.params.id[0] : route.params.id) ?? ''
const { content, loading, unavailable } = usePublicPhoto(id)

const viewerOpen = ref(false)
const formatter = new Intl.DateTimeFormat('zh-CN', {
  timeZone: 'Asia/Shanghai',
  dateStyle: 'long',
})

const ogVariant = computed(() => content.value?.asset.variants.find(variant => variant.name === 'w1920')
  ?? content.value?.asset.variants.at(-1))
usePageSeo({
  title: computed(() => content.value ? `${content.value.photo.title} · McAlbum` : '照片档案 · McAlbum'),
  description: computed(() => content.value?.photo.description ?? '读取服务器世界中已经发布的照片档案。'),
  image: computed(() => ogVariant.value ? `/${ogVariant.value.storageKey.replace(/^variants\//, 'media/')}` : undefined),
  type: 'article',
})
</script>

<template>
  <main v-if="content" id="main-content" class="photo-detail">
    <header class="photo-detail__header page-container">
      <div>
        <p class="section-kicker">照片档案</p>
        <h1>{{ content.photo.title }}</h1>
      </div>
      <ArchiveStamp
        :date="content.photo.capturedAt.slice(0, 10)"
        :world-day="content.photo.worldDay"
      />
    </header>

    <button class="photo-detail__image" type="button" aria-label="打开大图查看器" @click="viewerOpen = true">
      <AppMedia :asset="content.asset" eager sizes="100vw" />
    </button>

    <div class="photo-detail__body page-container">
      <article>
        <p class="photo-detail__description">{{ content.photo.description }}</p>
        <p class="photo-detail__alt"><strong>画面说明：</strong>{{ content.asset.altText }}</p>
        <ul class="tag-list" aria-label="照片标签">
          <li v-for="tag in content.photo.tags" :key="tag"><NuxtLink :to="`/album?tag=${encodeURIComponent(tag)}`">{{ tag }}</NuxtLink></li>
        </ul>
      </article>
      <aside>
        <dl class="detail-facts">
          <div><dt>拍摄日期</dt><dd><time :datetime="content.photo.capturedAt">{{ formatter.format(new Date(content.photo.capturedAt)) }}</time></dd></div>
          <div><dt>状态</dt><dd>编辑草稿</dd></div>
        </dl>
        <RelatedContentList :items="[
          ...content.stories.map(story => ({ title: story.title, meta: '历史专题', to: `/stories/${story.id}` })),
        ]" />
        <div class="photo-detail__actions">
          <a class="photo-detail__download" :href="content.asset.originalUrl" download>下载原图</a>
          <ShareButton :title="content.photo.title" :text="content.photo.description" />
        </div>
      </aside>
    </div>

    <section class="comments-section page-container" aria-labelledby="comments-title">
      <h2 id="comments-title">照片评论</h2>
      <PhotoComments :photo-id="content.photo.id" :initial-comments="content.photo.comments" />
    </section>

    <section v-if="content.relatedPhotos.length" class="related-photos page-container" aria-labelledby="related-title">
      <h2 id="related-title">相似标签的记录</h2>
      <div class="related-photos__grid">
        <NuxtLink v-for="entry in content.relatedPhotos" :key="entry.photo.id" :to="`/photos/${entry.photo.id}`">
          <AppMedia :asset="entry.asset" sizes="(max-width: 640px) 100vw, 33vw" />
          <span>{{ entry.photo.title }}</span>
        </NuxtLink>
      </div>
    </section>

    <ImageLightbox :asset="viewerOpen ? content.asset : null" :title="content.photo.title" @close="viewerOpen = false" />
  </main>
  <main v-else id="main-content" class="listing-page page-container">
    <EmptyState
      :title="loading ? '正在读取照片档案' : '这张照片尚未入藏'"
      :description="unavailable ? '公开 API 暂时不可用，请稍后刷新页面。' : '照片可能尚未发布，或已经归档。'"
    />
  </main>
</template>
