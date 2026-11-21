<script setup lang="ts">
import { getPlayerIndexContent } from '~/repositories/json-content'

const { players } = getPlayerIndexContent()
usePageSeo({ title: '玩家志 · 数字影集', description: '由玩家本人确认后公开的服务器居民档案。' })
</script>

<template>
  <main id="main-content" class="players-page page-container page-container--wide">
    <header class="page-intro">
      <p class="section-kicker">玩家志</p>
      <h1>同行者</h1>
    </header>
    <ul v-if="players.length" class="player-grid">
      <li v-for="player in players" :key="player.id">
        <NuxtLink :to="`/players/${player.id}`">
          <span aria-hidden="true">{{ player.name.slice(0, 1) }}</span>
          <div><h2>{{ player.name }}</h2><p>{{ player.bio }}</p></div>
        </NuxtLink>
      </li>
    </ul>
    <EmptyState
      v-else
      title="玩家档案等待本人确认"
      description="收到玩家本人确认的昵称、自我介绍和公开许可后，档案才会在这里出现。"
    />
    <NuxtLink class="text-link" to="/album">先从没有身份标注的照片开始浏览</NuxtLink>
  </main>
</template>
