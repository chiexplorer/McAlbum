<script setup lang="ts">
const route = useRoute()
const config = useRuntimeConfig()
const canonical = computed(() => `${String(config.public.siteUrl).replace(/\/$/, '')}${route.path}`)

useHead(() => ({
  titleTemplate: title => title ? `${title}` : 'McAlbum · 世界档案馆',
  link: [{ rel: 'canonical', href: canonical.value }],
}))
</script>

<template>
  <div class="site-shell">
    <a class="skip-link" href="#main-content">跳到主要内容</a>
    <SiteHeader />
    <NuxtPage />
    <footer class="site-footer">
      <div class="page-container site-footer__inner">
        <p>McAlbum · 一座由玩家共同整理的世界档案馆</p>
        <p>时间按中国北京（UTC+08:00）记录</p>
      </div>
    </footer>
  </div>
</template>
