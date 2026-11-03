<script setup lang="ts">
import { getPlayerContent } from '~/repositories/json-content'

const route = useRoute()
const id = (Array.isArray(route.params.id) ? route.params.id[0] : route.params.id) ?? ''
const content = getPlayerContent(id)
if (!content) throw createError({ statusCode: 404, statusMessage: '这份玩家档案不存在，或尚未获得公开许可' })

usePageSeo({ title: `${content.player.name} · 玩家志 · McAlbum`, description: content.player.bio })
</script>

<template>
  <main id="main-content" class="player-detail page-container">
    <header class="page-intro">
      <p class="section-kicker">玩家志 · {{ content.player.status === 'historical' ? '历史居民' : '当前居民' }}</p>
      <h1>{{ content.player.name }}</h1>
      <p>{{ content.player.bio }}</p>
    </header>
    <section class="player-profile">
      <AppMedia v-if="content.avatarAsset" :asset="content.avatarAsset" />
      <dl class="detail-facts">
        <div><dt>加入时间</dt><dd>{{ content.player.joinedAt ?? '待本人补充' }}</dd></div>
        <div><dt>代表作品</dt><dd>{{ content.works.length }} 篇</dd></div>
      </dl>
    </section>
    <RelatedContentList :items="[
      ...content.works.map(story => ({ title: story.title, meta: '历史专题', to: `/stories/${story.id}` })),
    ]" />
  </main>
</template>
