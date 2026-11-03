<script setup lang="ts">
const props = defineProps<{ error: { statusCode?: number; statusMessage?: string; message?: string } }>()
useSeoMeta({ title: `${props.error.statusCode ?? 500} · 档案未找到 · McAlbum`, robots: 'noindex' })
</script>

<template>
  <main id="main-content" class="error-page page-container">
    <div class="error-page__scene" aria-hidden="true"><span>?</span></div>
    <p class="error-page__code">{{ error.statusCode ?? 500 }}</p>
    <h1>{{ error.statusCode === 404 ? '这位迷路的玩家没有找到档案' : '档案馆暂时熄灯了' }}</h1>
    <p>{{ error.statusMessage ?? error.message ?? '页面可能已经移动，或内容还没有公开。' }}</p>
    <div class="error-page__links"><NuxtLink class="text-link" to="/">返回世界首页</NuxtLink><NuxtLink to="/album">去相册继续翻阅</NuxtLink></div>
  </main>
</template>
