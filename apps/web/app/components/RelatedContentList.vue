<script setup lang="ts">
defineProps<{ items: Array<{ title: string; meta: string; to?: string }> }>()
</script>

<template>
  <ul class="related-list">
    <li v-for="item in items" :key="`${item.title}-${item.meta}`">
      <NuxtLink v-if="item.to" :to="item.to">
        <span>{{ item.title }}</span><small>{{ item.meta }}</small>
      </NuxtLink>
      <div v-else>
        <span>{{ item.title }}</span><small>{{ item.meta }}</small>
      </div>
    </li>
  </ul>
</template>
