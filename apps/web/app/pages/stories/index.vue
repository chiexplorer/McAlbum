<script setup lang="ts">
const { stories, refreshing, usingSnapshot } = usePublicStories()
usePageSeo({
  title: '历史作品集 · McAlbum',
  description: '以作品集形式阅读服务器的建设、活动与共同经历。',
})
</script>

<template>
  <main id="main-content" class="listing-page page-container">
    <header class="page-intro">
      <p class="section-kicker">历史作品集</p>
      <h1>每一次相聚，都有自己的章节。</h1>
      <p>专题不是照片堆叠，而是把场景、经过与余韵重新编成一条可以阅读的路线。</p>
      <p v-if="usingSnapshot && !refreshing" class="content-sync-note">当前展示离线快照；公开 API 恢复后刷新页面即可同步最新内容。</p>
    </header>

    <section class="portfolio-grid" aria-label="历史专题列表">
      <NuxtLink v-for="entry in stories" :key="entry.story.id" :to="`/stories/${entry.story.id}`" class="portfolio-card">
        <AppMedia :asset="entry.coverAsset" sizes="(max-width: 720px) 100vw, 70vw" />
        <div>
          <p class="section-kicker">历史专题</p>
          <h2>{{ entry.story.title }}</h2>
          <p>{{ entry.story.summary }}</p>
          <span>进入作品集 →</span>
        </div>
      </NuxtLink>
    </section>

    <EmptyState v-if="stories.length === 0" title="还没有公开作品集" description="作品集发布后，刷新页面即可在这里看到。" />

    <aside class="material-callout">
      <p class="section-kicker">档案仍在生长</p>
      <p>现有素材集中在一次中秋活动。补充施工过程、其他地点和不同时期的记录后，这里会自然长成服务器历史。</p>
    </aside>
  </main>
</template>
