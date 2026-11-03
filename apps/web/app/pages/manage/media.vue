<script setup lang="ts">
interface MediaItem {
  id: string
  alt_text: string
  captured_at: string
  focal_x: number
  focal_y: number
  width: number
  height: number
  processing_status: string
  variants: Array<{ name: string, url: string, width: number, height: number }>
}

const api = useManageApi()
const items = ref<MediaItem[]>([])
useHead({ title: '媒体库 · McAlbum' })

onMounted(async () => {
  if (!await api.restore()) return
  items.value = await api.request('/manage/media')
})

function preview(item: MediaItem) {
  return item.variants.find(variant => variant.name === 'w480')?.url || item.variants.at(-1)?.url
}
</script>

<template>
  <ManageShell>
    <header class="manage-heading"><p class="section-kicker">高级管理</p><h1>媒体库</h1><p>这里保存已经处理完成的原图记录和公开变体。日常新增内容请从“上传照片”进入，系统会同时完成媒体入库和照片草稿创建。</p></header>
    <NuxtLink class="manage-primary" to="/manage/photos">上传照片</NuxtLink>
    <section class="manage-library"><h2>已入库媒体</h2><div class="manage-media-grid"><article v-for="item in items" :key="item.id"><img v-if="preview(item)" :src="preview(item)" :alt="item.alt_text" loading="lazy"><div><code>{{ item.id }}</code><p>{{ item.alt_text }}</p><span>{{ item.width }} × {{ item.height }}</span></div></article></div></section>
  </ManageShell>
</template>
